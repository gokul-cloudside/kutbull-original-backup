
from views.staff import *
from django.utils.translation import ugettext_lazy as _
from .settings import ERROR_CODES
from .models import Queue, Ticket, TicketChange, FollowUp
from .lib import send_templated_mail, safe_template_context
from .models import TicketAssociation
from views.staff import calc_basic_ticket_stats
import logging
from helpdesk.analyse import analyse_ticket

logger = logging.getLogger('dataglen.rest_views')
logger.setLevel(logging.DEBUG)

"""
    plant - actual instance of a Solar Plant for which the tikcet is being created
    PRIORITY_CHOICES = (
        (1, _('1. Critical')),
        (2, _('2. High')),
        (3, _('3. Normal')),
        (4, _('4. Low')),
        (5, _('5. Very Low')),
    )
    due_date - dt object,
    ticket_name - name,
    event_description - ticket description,
    associations_dict - a dict {source_key: (event_name, event_code, identifiername, ts)}
    open_comment - comment for the first followup,
    user - if it needs to be assigned to a user,
    send_email - True/False to send emails
"""

def create_ticket(plant, priority, due_date,
                  ticket_name, ticket_description, event_type,
                  open_comment, user=None, send_email=False):
    """
    Writes and returns a Ticket() object
    """

    # ticket won't be assigned to anyone yet though
    if user:
        assignable_users = [x.user for x in plant.organization_users.all()]
        assert(user in assignable_users)

    try:
        q = Queue.objects.get(plant=plant)
        submitter_email = str(q.email_address) if q.from_address else None
        # new ticket
        t = Ticket( title = ticket_name,
                    submitter_email = submitter_email,
                    event_type = event_type,
                    created = timezone.now(),
                    status = Ticket.OPEN_STATUS,
                    queue = q,
                    description = ticket_description,
                    priority = priority,
                    due_date = due_date,
                  )

        # the ticket has not been assigned to anyone yet
        if user:
            t.assigned_to = user
        else:
            t.assigned_to = None
        t.save()

        logger.debug("tc: %s %s %s %s" %(t.id, t.status, t.event_type, t.submitter_email))

        # followup
        f = FollowUp(   ticket = t,
                        title = _('Ticket Opened'),
                        date = timezone.now(),
                        public = True,
                        comment = open_comment,
                        user = plant.owner.organization_user.user,
                     )
        f.title = _('Ticket Opened')
        f.save()

        # send emails to the site engineers
        if send_email:
            messages_sent_to = []
            context = safe_template_context(t)
            # create email content based on the FollowUp that has been created
            context['comment'] = f.comment
            if t.submitter_email:
                send_templated_mail(
                    'newticket_submitter',
                    context,
                    recipients=t.submitter_email,
                    sender=q.from_address,
                    fail_silently=True,
                    )
                messages_sent_to.append(t.submitter_email)

            '''if user and t.assigned_to \
                    and t.assigned_to != user \
                    and t.assigned_to.usersettings.settings.get('email_on_ticket_assign', False) \
                    and t.assigned_to.email \
                    and t.assigned_to.email not in messages_sent_to:
                send_templated_mail(
                    'assigned_owner',
                    context,
                    recipients=t.assigned_to.email,
                    sender=q.from_address,
                    fail_silently=True,
                    )
                messages_sent_to.append(t.assigned_to.email)'''

            if q.new_ticket_cc and q.new_ticket_cc not in messages_sent_to:
                send_templated_mail(
                    'newticket_cc',
                    context,
                    recipients=q.new_ticket_cc,
                    sender=q.from_address,
                    fail_silently=True,
                    )
                messages_sent_to.append(q.new_ticket_cc)

            if q.updated_ticket_cc \
                    and q.updated_ticket_cc != q.new_ticket_cc \
                    and q.updated_ticket_cc not in messages_sent_to:
                send_templated_mail(
                    'newticket_cc',
                    context,
                    recipients=q.updated_ticket_cc,
                    sender=q.from_address,
                    fail_silently=True,
                )

        return t
    except AssertionError:
        return ERROR_CODES.INVALID_USER
    except Queue.DoesNotExist:
        return ERROR_CODES.NO_QUEUE
    except Exception as exception:
        print(str(exception))
        return -1


"""
    owner = id of the new user if the owner is changing, set it to 0 to unassign a ticket
"""


def update_ticket(plant, ticket_id, followup_user, comment='', new_status=None,
                  title='', public=False, owner=-1, priority=None, due_date = None,
                  escalation_level=0):

    ticket = get_object_or_404(Ticket, id=ticket_id)

    try:
        assert(len(ticket.associations.filter(active=True)) == 0)
    except AssertionError:
        return "There are active associations with this ticket, please update them first."

    if new_status is None:
        new_status = ticket.status

    if new_status and int(new_status) == 6:
        ticket.assigned_to = followup_user

    if title is None:
        title = ticket.title

    if priority is None:
        priority = ticket.priority

    if not due_date:
        due_date = ticket.due_date
    else:
        due_date = due_date

    if escalation_level == 0:
        last_escalation = None
    else:
       last_escalation = timezone.now()

    no_changes = all([
        not comment,
        new_status == ticket.status,
        title == ticket.title,
        priority == int(ticket.priority),
        due_date == ticket.due_date,
        (owner == -1) or (not owner and not ticket.assigned_to) or (owner and User.objects.get(id=owner) == ticket.assigned_to),
    ])
    if no_changes:
        return True

    # We need to allow the 'ticket' and 'queue' contexts to be applied to the
    # comment.
    from django.template import loader, Context
    context = safe_template_context(ticket)
    # this line sometimes creates problems if code is sent as a comment.
    # if comment contains some django code, like "why does {% if bla %} crash",
    # then the following line will give us a crash, since django expects {% if %}
    # to be closed with an {% endif %} tag.

    # get_template_from_string was removed in Django 1.8 http://django.readthedocs.org/en/1.8.x/ref/templates/upgrading.html
    try:
        from django.template import engines
        template_func = engines['django'].from_string
    except ImportError:  # occurs in django < 1.8
        return False

    # RemovedInDjango110Warning: render() must be called with a dict, not a Context.
    if VERSION < (1, 8):
        context = Context(context)

    comment = template_func(comment).render(context)

    if owner is -1 and ticket.assigned_to:
        owner = ticket.assigned_to.id

    f = FollowUp(ticket=ticket, date=timezone.now(), comment=comment)

    f.user = followup_user
    f.public = public

    reassigned = False

    if owner is not -1:
        if owner != 0 and ((ticket.assigned_to and owner != ticket.assigned_to.id) or not ticket.assigned_to):
            assignable_users = [x.user.id for x in plant.organization_users.all()]
            assert(owner in assignable_users)
            new_user = User.objects.get(id=owner)
            f.title = _('Assigned to %(username)s') % {
                'username': new_user.get_username(),
                }
            ticket.assigned_to = new_user
            reassigned = True
        # user changed owner to 'unassign'
        elif owner == 0 and ticket.assigned_to is not None:
            f.title = _('Unassigned')
            ticket.assigned_to = None

    if new_status != ticket.status:
        ticket.status = new_status
        ticket.save()
        f.new_status = new_status
        if f.title:
            f.title += ' and %s' % ticket.get_status_display()
        else:
            f.title = '%s' % ticket.get_status_display()

    if not f.title:
        if f.comment:
            f.title = _('Comment')
        else:
            f.title = _('Updated')

    f.save()

    if title != ticket.title:
        c = TicketChange(
            followup=f,
            field=_('Title'),
            old_value=ticket.title,
            new_value=title,
            )
        c.save()
        ticket.title = title

    if priority != ticket.priority:
        c = TicketChange(
            followup=f,
            field=_('Priority'),
            old_value=ticket.priority,
            new_value=priority,
            )
        c.save()
        ticket.priority = priority

    if due_date != ticket.due_date:
        c = TicketChange(
            followup=f,
            field=_('Due on'),
            old_value=ticket.due_date,
            new_value=due_date,
            )
        c.save()
        ticket.due_date = due_date

    if last_escalation:
        c = TicketChange(
            followup=f,
            field=_('last_escalation'),
            old_value=ticket.last_escalation,
            new_value=last_escalation,
            )
        c.save()
        ticket.last_escalation = last_escalation

    if last_escalation:
        c = TicketChange(
            followup=f,
            field=_('escalation_level'),
            old_value=ticket.escalation_level,
            new_value=escalation_level,
            )
        c.save()
        ticket.escalation_level = escalation_level

    if new_status in [ Ticket.RESOLVED_STATUS, Ticket.CLOSED_STATUS ]:
        if new_status == Ticket.RESOLVED_STATUS or ticket.resolution is None:
            ticket.resolution = comment

    messages_sent_to = []

    # ticket might have changed above, so we re-instantiate context with the
    # (possibly) updated ticket.
    context = safe_template_context(ticket)
    context.update(
        resolution=ticket.resolution,
        comment=f.comment,
        )

    if public and (f.comment or (f.new_status in (Ticket.RESOLVED_STATUS, Ticket.CLOSED_STATUS))):
        if f.new_status == Ticket.RESOLVED_STATUS:
            template = 'resolved_'
        elif f.new_status == Ticket.CLOSED_STATUS:
            template = 'closed_'
        else:
            template = 'updated_'

        template_suffix = 'submitter'

        if ticket.submitter_email:
            send_templated_mail(
                template + template_suffix,
                context,
                recipients=ticket.submitter_email,
                sender=ticket.queue.from_address,
                fail_silently=True,
                )
            messages_sent_to.append(ticket.submitter_email)

        template_suffix = 'cc'

        for cc in ticket.ticketcc_set.all():
            if cc.email_address not in messages_sent_to:
                send_templated_mail(
                    template + template_suffix,
                    context,
                    recipients=cc.email_address,
                    sender=ticket.queue.from_address,
                    fail_silently=True,
                    )
                messages_sent_to.append(cc.email_address)

    # if ticket.assigned_to and ticket.assigned_to.email and ticket.assigned_to.email not in messages_sent_to:
    #     # We only send e-mails to staff members if the ticket is updated by
    #     # another user. The actual template varies, depending on what has been
    #     # changed.
    #     if reassigned:
    #         template_staff = 'assigned_owner'
    #     elif f.new_status == Ticket.RESOLVED_STATUS:
    #         template_staff = 'resolved_owner'
    #     elif f.new_status == Ticket.CLOSED_STATUS:
    #         template_staff = 'closed_owner'
    #     else:
    #         template_staff = 'updated_owner'
    #
    #     if (not reassigned or ( reassigned and ticket.assigned_to.usersettings.settings.get('email_on_ticket_assign', False))) or (not reassigned and ticket.assigned_to.usersettings.settings.get('email_on_ticket_change', False)):
    #         send_templated_mail(
    #             template_staff,
    #             context,
    #             recipients=ticket.assigned_to.email,
    #             sender=ticket.queue.from_address,
    #             fail_silently=True,
    #             )
    #         messages_sent_to.append(ticket.assigned_to.email)
    # logger.debug("there are changes, updating11")
    #
    # if ticket.queue.updated_ticket_cc and ticket.queue.updated_ticket_cc not in messages_sent_to:
    #     if reassigned:
    #         template_cc = 'assigned_cc'
    #     elif f.new_status == Ticket.RESOLVED_STATUS:
    #         template_cc = 'resolved_cc'
    #     elif f.new_status == Ticket.CLOSED_STATUS:
    #         template_cc = 'closed_cc'
    #     else:
    #         template_cc = 'updated_cc'
    #
    #     send_templated_mail(
    #         template_cc,
    #         context,
    #         recipients=ticket.queue.updated_ticket_cc,
    #         sender=ticket.queue.from_address,
    #         fail_silently=True,
    #         )
    # logger.debug("there are changes, updating12")

    ticket.save()

    if new_status == Ticket.CLOSED_STATUS:
        try:
            logger.debug("scheduling an offline job to be processed after 15 minutes")
            analyse_ticket.apply_async(args=[ticket.id], countdown=60*30)
        except Exception as exc:
            logger.debug("error scheduling an offline job: " + str(exc))
            pass

    return True


def get_plant_tickets(plant):
    """
    A quick summary overview for users: A list of their own tickets, a table
    showing ticket counts by queue/status, and a list of unassigned tickets
    with options for them to 'Take' ownership of said tickets.
    """
    t_stats = {}
    # get the queues associated with these plants

    try:
        queue = Queue.objects.get(plant=plant)
    except Queue.DoesNotExist:
        return -1

    open_unassigned_tickets = Ticket.objects.filter(
            assigned_to__isnull=True,
            queue=queue,
        ).exclude(
            status__in = [Ticket.CLOSED_STATUS, Ticket.RESOLVED_STATUS],
        )
    t_stats['open_unassigned_tickets'] = open_unassigned_tickets

    # open & reopened tickets, assigned to current user
    open_assigned_tickets = Ticket.objects.filter(
            assigned_to__isnull=False,
            queue=queue,
        ).exclude(
            status__in = [Ticket.CLOSED_STATUS, Ticket.RESOLVED_STATUS],
        )
    t_stats['open_assigned_tickets'] = open_assigned_tickets

    # closed & resolved tickets, assigned to current user
    tickets_closed_resolved =  Ticket.objects.filter(
            queue=queue,
            status__in = [Ticket.CLOSED_STATUS, Ticket.RESOLVED_STATUS])
    t_stats['tickets_closed_resolved'] = tickets_closed_resolved


    Tickets = Ticket.objects.filter(
                queue=queue,
            )
    basic_ticket_stats = calc_basic_ticket_stats(Tickets)
    t_stats['basic_ticket_stats'] = basic_ticket_stats

    return t_stats


def get_plant_tickets_date(plant, start_date, end_date):
    """
    A quick summary overview for users: A list of their own tickets, a table
    showing ticket counts by queue/status, and a list of unassigned tickets
    with options for them to 'Take' ownership of said tickets.
    """
    t_stats = {}
    # get the queues associated with these plants

    try:
        queue = Queue.objects.get(plant=plant)
    except Queue.DoesNotExist:
        return -1

    open_unassigned_tickets = Ticket.objects.filter(
            assigned_to__isnull=True,
            queue=queue,
            created__gte = start_date,
            created__lt = end_date
        ).exclude(
            status__in = [Ticket.CLOSED_STATUS, Ticket.RESOLVED_STATUS],
        )
    t_stats['open_unassigned_tickets'] = open_unassigned_tickets

    # open & reopened tickets, assigned to current user
    open_assigned_tickets = Ticket.objects.filter(
            assigned_to__isnull=False,
            queue=queue,
            created__gte = start_date,
            created__lt = end_date
        ).exclude(
            status__in = [Ticket.CLOSED_STATUS, Ticket.RESOLVED_STATUS],
        )
    t_stats['open_assigned_tickets'] = open_assigned_tickets

    # closed & resolved tickets, assigned to current user
    tickets_closed_resolved =  Ticket.objects.filter(
            queue=queue,
            modified__gte = start_date,
            modified__lt = end_date,
            status__in = [Ticket.CLOSED_STATUS, Ticket.RESOLVED_STATUS])
    t_stats['tickets_closed_resolved'] = tickets_closed_resolved


    Tickets = Ticket.objects.filter(
                queue=queue,
                modified__gte = start_date,
                modified__lt = end_date
            )
    basic_ticket_stats = calc_basic_ticket_stats(Tickets)
    t_stats['basic_ticket_stats'] = basic_ticket_stats

    return t_stats


'''
New set of functions
def plant_tickets(plant, event_type, status, latest=True, st=None, et=None, group=None) :
def device_tickets(identifier, event_type, status, latest=True, st=None, et=None):
'''



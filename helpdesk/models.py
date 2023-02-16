
from __future__ import unicode_literals
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.contrib.auth import get_user_model
from django.conf import settings
from django.utils.translation import ugettext_lazy as _, ugettext
from django import VERSION
from django.utils.encoding import python_2_unicode_compatible
from solarrms.models import SolarPlant, InverterStatusMappings, InverterErrorCodes, IndependentInverter
import logging
from django.db.models import Q
from .utils import send_infini_sms
from dataglen.models import Sensor
from django.core.exceptions import ValidationError
from helpdesk.data_uploader import send_new_alarm, send_close_alarm
from helpdesk.utils import prepare_descriptions, prepare_descriptions_close
from datetime import timedelta
import json

logger = logging.getLogger('helpdesk.models')
logger.setLevel(logging.DEBUG)

from helpdesk.analyse import analyse_association
from django.db import connection

try:
    from django.utils import timezone
except ImportError:
    from datetime import datetime as timezone



EVENT_TYPE = [('GATEWAY_POWER_OFF', 'GATEWAY_POWER_OFF'),
            ('GATEWAY_DISCONNECTED', 'GATEWAY_DISCONNECTED'),
            ('INVERTERS_DISCONNECTED', 'INVERTERS_DISCONNECTED'),
            ('AJBS_DISCONNECTED', 'AJBS_DISCONNECTED'),
            ('INVERTERS_NOT_GENERATING', 'INVERTERS_NOT_GENERATING'),
            ('INVERTERS_ALARMS', 'INVERTERS_ALARMS'),
            ('AJB_STRING_CURRENT_ZERO_ALARM', 'AJB_STRING_CURRENT_ZERO_ALARM'),
            ('PANEL_CLEANING', 'PANEL_CLEANING'),
            ('INVERTERS_UNDERPERFORMING', 'INVERTERS_UNDERPERFORMING'),
            ('MPPT_UNDERPERFORMING', 'MPPT_UNDERPERFORMING'),
            ('AJB_UNDERPERFORMING', 'AJB_UNDERPERFORMING'),
            ('CUSTOM_TICKET', 'CUSTOM_TICKET')]

EVENT_TYPE_TO_FEATURE_MAPPING = {
    'GATEWAY_POWER_OFF': 'GATEWAY_ALERTS',
    'GATEWAY_DISCONNECTED': 'GATEWAY_ALERTS',
    'INVERTERS_DISCONNECTED': 'INVERTER_ALERTS',
    'AJBS_DISCONNECTED': 'SMB_ALERTS',
    'INVERTERS_ALARMS': 'INVERTER_ALERTS',
    'AJB_STRING_CURRENT_ZERO_ALARM': 'SMB_ALERTS',
    'PANEL_CLEANING': 'CLEANING',
    'INVERTERS_UNDERPERFORMING': 'INVERTER_COMPARISON',
    'MPPT_UNDERPERFORMING': 'SMB_COMPARISON',
    'AJB_UNDERPERFORMING': 'MPPT_COMPARISON',
    'CUSTOM_TICKET' : 'OPEN_TICKETS',
}

ENERGY_LOSS_CAUSE = [('GRID_NOT_AVAILABLE', 'GRID_UNAVAILABILITY'),
                     ('NO_INVERTER_GENERATION', 'NO_INVERTER_GENERATION'),
                     ('INVERTER_INTERNAL_ALARMS', 'INVERTER_INTERNAL_ALARMS'),
                     ('SOILING_LOSS', 'SOILING_LOSS'),
                     ('INVERTER_UNDERPERFORMING', 'INVERTER_UNDERPERFORMING'),
                     ('MPPT_UNDERPERFORMING', 'MPPT_UNDERPERFORMING'),
                     ('STRING_UNDERPERFORMING', 'STRING_UNDERPERFORMING')]



'''
alarms_descriptions.append("/".join([Sensor.objects.get(sourceKey=identifier).name,
                                     "STATUS:" + str(alarms_dict[identifier]['solar_status']),
                                     "ALARM: " + ",".join(alarms_dict[identifier]['alarm_codes'])]))
alarms_descriptions.append("/".join([Sensor.objects.get(sourceKey=identifier).name,
                                     "STATUS:" + str(alarms_dict[identifier]['solar_status'])]))

'''

def get_solar_status_code_mapping(identifier, solar_status):
    try:
        plant = IndependentInverter.objects.get(sourceKey=identifier).plant
        inverter_status_mapping = InverterStatusMappings.objects.get(plant=plant,
                                                                     stream_name='SOLAR_STATUS',
                                                                     status_code=float(
                                                                         solar_status))
        device_status_description = inverter_status_mapping.status_description
        return device_status_description
    except:
        return str(solar_status)


def get_alarm_code_name(identifier, alarm_code):
    try:
        inv = IndependentInverter.objects.get(sourceKey=identifier)
        inv_error_codes = InverterErrorCodes.objects.filter(manufacturer__in=[inv.manufacturer.upper(), inv.manufacturer], error_code=alarm_code)
        alarm_description = inv_error_codes[0].error_description
        return alarm_description
    except:
        return str(alarm_code)


@python_2_unicode_compatible
class Queue(models.Model):
    """
    A queue is a collection of tickets into what would generally be business
    areas or departments.

    For example, a company may have a queue for each Product they provide, or
    a queue for each of Accounts, Pre-Sales, and Support.

    """

    title = models.CharField(
        _('Title'),
        max_length=100,
        )

    plant = models.ForeignKey(
        SolarPlant,
        related_name="queues"
    )

    slug = models.SlugField(
        _('Slug'),
        max_length=50,
        unique=True,
        help_text=_('This slug is used when building ticket ID\'s. Once set, '
            'try not to change it or e-mailing may get messy.'),
        )

    email_address = models.EmailField(
        _('E-Mail Address'),
        blank=True,
        null=True,
        help_text=_('All outgoing e-mails for this queue will use this e-mail '
            'address. If you use IMAP or POP3, this should be the e-mail '
            'address for that mailbox.'),
        )

    locale = models.CharField(
        _('Locale'),
        max_length=10,
        blank=True,
        null=True,
        help_text=_('Locale of this queue. All correspondence in this queue will be in this language.'),
        )

    allow_public_submission = models.BooleanField(
        _('Allow Public Submission?'),
        blank=True,
        default=False,
        help_text=_('Should this queue be listed on the public submission '
            'form?'),
        )

    allow_email_submission = models.BooleanField(
        _('Allow E-Mail Submission?'),
        blank=True,
        default=False,
        help_text=_('Do you want to poll the e-mail box below for new '
            'tickets?'),
        )

    escalate_days = models.IntegerField(
        _('Escalation Days'),
        blank=True,
        null=True,
        help_text=_('For tickets which are not held, how often do you wish to '
            'increase their priority? Set to 0 for no escalation.'),
        )

    new_ticket_cc = models.CharField(
        _('New Ticket CC Address'),
        blank=True,
        null=True,
        max_length=200,
        help_text=_('If an e-mail address is entered here, then it will '
            'receive notification of all new tickets created for this queue. '
            'Enter a comma between multiple e-mail addresses.'),
        )

    new_ticket_sms = models.CharField(
        _('New Ticket SMS numbers'),
        blank=True,
        null=True,
        max_length=200,
        help_text=_('If a phone number is entered here, then it will '
            'receive notification of all new tickets created for this queue. '
            'Enter a comma between multiple numbers.'),
        )

    updated_ticket_cc = models.CharField(
        _('Updated Ticket CC Address'),
        blank=True,
        null=True,
        max_length=200,
        help_text=_('If an e-mail address is entered here, then it will '
            'receive notification of all activity (new tickets, closed '
            'tickets, updates, reassignments, etc) for this queue. Separate '
            'multiple addresses with a comma.'),
        )

    email_box_type = models.CharField(
        _('E-Mail Box Type'),
        max_length=5,
        choices=(('pop3', _('POP 3')), ('imap', _('IMAP'))),
        blank=True,
        null=True,
        help_text=_('E-Mail server type for creating tickets automatically '
            'from a mailbox - both POP3 and IMAP are supported.'),
        )

    email_box_host = models.CharField(
        _('E-Mail Hostname'),
        max_length=200,
        blank=True,
        null=True,
        help_text=_('Your e-mail server address - either the domain name or '
            'IP address. May be "localhost".'),
        )

    email_box_port = models.IntegerField(
        _('E-Mail Port'),
        blank=True,
        null=True,
        help_text=_('Port number to use for accessing e-mail. Default for '
            'POP3 is "110", and for IMAP is "143". This may differ on some '
            'servers. Leave it blank to use the defaults.'),
        )

    email_box_ssl = models.BooleanField(
        _('Use SSL for E-Mail?'),
        blank=True,
        default=False,
        help_text=_('Whether to use SSL for IMAP or POP3 - the default ports '
            'when using SSL are 993 for IMAP and 995 for POP3.'),
        )

    email_box_user = models.CharField(
        _('E-Mail Username'),
        max_length=200,
        blank=True,
        null=True,
        help_text=_('Username for accessing this mailbox.'),
        )

    email_box_pass = models.CharField(
        _('E-Mail Password'),
        max_length=200,
        blank=True,
        null=True,
        help_text=_('Password for the above username'),
        )

    email_box_imap_folder = models.CharField(
        _('IMAP Folder'),
        max_length=100,
        blank=True,
        null=True,
        help_text=_('If using IMAP, what folder do you wish to fetch messages '
            'from? This allows you to use one IMAP account for multiple '
            'queues, by filtering messages on your IMAP server into separate '
            'folders. Default: INBOX.'),
        )

    permission_name = models.CharField(
        _('Django auth permission name'),
        max_length=50,
        blank=True,
        null=True,
        editable=False,
        help_text=_('Name used in the django.contrib.auth permission system'),
        )


    email_box_interval = models.IntegerField(
        _('E-Mail Check Interval'),
        help_text=_('How often do you wish to check this mailbox? (in Minutes)'),
        blank=True,
        null=True,
        default='5',
        )

    email_box_last_check = models.DateTimeField(
        blank=True,
        null=True,
        editable=False,
        # This is updated by management/commands/get_mail.py.
        )

    socks_proxy_type = models.CharField(
        _('Socks Proxy Type'),
        max_length=8,
        choices=(('socks4', _('SOCKS4')), ('socks5', _('SOCKS5'))),
        blank=True,
        null=True,
        help_text=_('SOCKS4 or SOCKS5 allows you to proxy your connections through a SOCKS server.'),
    )

    socks_proxy_host = models.GenericIPAddressField(
        _('Socks Proxy Host'),
        blank=True,
        null=True,
        help_text=_('Socks proxy IP address. Default: 127.0.0.1'),
    )

    socks_proxy_port = models.IntegerField(
        _('Socks Proxy Port'),
        blank=True,
        null=True,
        help_text=_('Socks proxy port number. Default: 9150 (default TOR port)'),
    )

    default_owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='default_owner',
        blank=True,
        null=True,
        verbose_name=_('Default owner'),
    )

    def __str__(self):
        return "%s" % self.title

    class Meta:
        ordering = ('title',)
        verbose_name = _('Queue')
        verbose_name_plural = _('Queues')

    def _from_address(self):
        """
        Short property to provide a sender address in SMTP format,
        eg 'Name <email>'. We do this so we can put a simple error message
        in the sender name field, so hopefully the admin can see and fix it.
        """
        if not self.email_address:
            return u'NO QUEUE EMAIL ADDRESS DEFINED <%s>' % settings.DEFAULT_FROM_EMAIL
        else:
            return u'%s <%s>' % (self.title, self.email_address)
    from_address = property(_from_address)

    def prepare_permission_name(self):
        """Prepare internally the codename for the permission and store it in permission_name.
        :return: The codename that can be used to create a new Permission object.
        """
        # Prepare the permission associated to this Queue
        basename = "queue_access_%s" % self.slug
        self.permission_name = "helpdesk.%s" % basename
        return basename

    def save(self, *args, **kwargs):
        if self.email_box_type == 'imap' and not self.email_box_imap_folder:
            self.email_box_imap_folder = 'INBOX'

        if self.socks_proxy_type:
            if not self.socks_proxy_host:
                self.socks_proxy_host = '127.0.0.1'
            if not self.socks_proxy_port:
                self.socks_proxy_port = 9150
        else:
            self.socks_proxy_host = None
            self.socks_proxy_port = None

        if not self.email_box_port:
            if self.email_box_type == 'imap' and self.email_box_ssl:
                self.email_box_port = 993
            elif self.email_box_type == 'imap' and not self.email_box_ssl:
                self.email_box_port = 143
            elif self.email_box_type == 'pop3' and self.email_box_ssl:
                self.email_box_port = 995
            elif self.email_box_type == 'pop3' and not self.email_box_ssl:
                self.email_box_port = 110

        if not self.id:
            # Prepare the permission codename and the permission
            # (even if they are not needed with the current configuration)
            basename = self.prepare_permission_name()

            Permission.objects.create(
                name=_("Permission for queue: ") + self.title,
                content_type=ContentType.objects.get(model="queue"),
                codename=basename,
            )

        super(Queue, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        permission_name = self.permission_name
        super(Queue, self).delete(*args, **kwargs)

        # once the Queue is safely deleted, remove the permission (if exists)
        if permission_name:
            try:
                p = Permission.objects.get(codename=permission_name[9:])
                p.delete()
            except ObjectDoesNotExist:
                pass


class Ticket(models.Model):
    """
    To allow a ticket to be entered as quickly as possible, only the
    bare minimum fields are required. These basically allow us to
    sort and manage the ticket. The user can always go back and
    enter more information later.

    A good example of this is when a customer is on the phone, and
    you want to give them a ticket ID as quickly as possible. You can
    enter some basic info, save the ticket, give the customer the ID
    and get off the phone, then add in further detail at a later time
    (once the customer is not on the line).

    Note that assigned_to is optional - unassigned tickets are displayed on
    the dashboard to prompt users to take ownership of them.
    """

    OPEN_STATUS = 1
    ACKNOWLEDGED_STATUS = 6
    REOPENED_STATUS = 2
    RESOLVED_STATUS = 3
    CLOSED_STATUS = 4
    DUPLICATE_STATUS = 5

    STATUS_CHOICES = (
        (OPEN_STATUS, _('Open')),
        (ACKNOWLEDGED_STATUS, _('Acknowledged')),
        (REOPENED_STATUS, _('Reopened')),
        (RESOLVED_STATUS, _('Resolved')),
        (CLOSED_STATUS, _('Closed')),
        (DUPLICATE_STATUS, _('Duplicate')),
    )

    PRIORITY_CHOICES = (
        (1, _('1. Critical')),
        (2, _('2. High')),
        (3, _('3. Normal')),
        (4, _('4. Low')),
        (5, _('5. Very Low')),
    )

    title = models.CharField(
        _('Title'),
        max_length=400,
        )

    queue = models.ForeignKey(
        Queue,
        verbose_name=_('Queue'),
        related_query_name="tickets",
        related_name="ticket"
        )

    created = models.DateTimeField(
        _('Created'),
        blank=True,
        db_index=True,
        help_text=_('Date this ticket was first created'),
        )

    modified = models.DateTimeField(
        _('Modified'),
        blank=True,
        db_index=True,
        help_text=_('Date this ticket was most recently changed.'),
        )

    submitter_email = models.EmailField(
        _('Submitter E-Mail'),
        blank=True,
        null=True,
        help_text=_('The submitter will receive an email for all public '
            'follow-ups left for this task.'),
        )

    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='assigned_to',
        blank=True,
        null=True,
        verbose_name=_('Assigned to'),
        )

    status = models.IntegerField(
        _('Status'),
        db_index=True,
        choices=STATUS_CHOICES,
        default=OPEN_STATUS,
        )

    on_hold = models.BooleanField(
        _('On Hold'),
        blank=True,
        default=False,
        help_text=_('If a ticket is on hold, it will not automatically be '
            'escalated.'),
        )

    description = models.TextField(
        _('Description'),
        blank=True,
        null=True,
        help_text=_('The content of the customers query.'),
        )

    resolution = models.TextField(
        _('Resolution'),
        blank=True,
        null=True,
        help_text=_('The resolution provided to the customer by our staff.'),
        )

    priority = models.IntegerField(
        _('Priority'),
        choices=PRIORITY_CHOICES,
        default=3,
        blank=3,
        help_text=_('1 = Highest Priority, 5 = Low Priority'),
        )

    due_date = models.DateTimeField(
        _('Due on'),
        blank=True,
        null=True,
        )

    last_escalation = models.DateTimeField(
        blank=True,
        null=True,
        editable=True,
        help_text=_('The date this ticket was last escalated - updated '
            'automatically by management/commands/escalate_tickets.py.'),
        )

    escalation_level = models.IntegerField(
        blank=True,
        null=True,
        editable=True,
        default=0,
        help_text=_('The level to which this ticket has been escalated '),
        )

    def _get_assigned_to(self):
        """ Custom property to allow us to easily print 'Unassigned' if a
        ticket has no owner, or the users name if it's assigned. If the user
        has a full name configured, we use that, otherwise their username. """
        if not self.assigned_to:
            return _('Unassigned')
        else:
            if self.assigned_to.get_full_name():
                return self.assigned_to.get_full_name()
            else:
                return self.assigned_to.get_username()
    get_assigned_to = property(_get_assigned_to)

    def _get_ticket(self):
        """ A user-friendly ticket ID, which is a combination of ticket ID
        and queue slug. This is generally used in e-mail subjects. """

        return u"[%s]" % (self.ticket_for_url)
    ticket = property(_get_ticket)

    def _get_ticket_for_url(self):
        """ A URL-friendly ticket ID, used in links. """
        return u"%s-%s" % (self.queue.slug, self.id)
    ticket_for_url = property(_get_ticket_for_url)

    def _get_priority_img(self):
        """ Image-based representation of the priority """
        from django.conf import settings
        return u"%shelpdesk/priorities/priority%s.png" % (settings.MEDIA_URL, self.priority)
    get_priority_img = property(_get_priority_img)

    def _get_priority_css_class(self):
        """
        Return the boostrap class corresponding to the priority.
        """
        if self.priority == 2:
            return "warning"
        elif self.priority == 1:
            return "danger"
        else:
            return ""
    get_priority_css_class = property(_get_priority_css_class)

    def _get_status(self):
        """
        Displays the ticket status, with an "On Hold" message if needed.
        """
        held_msg = ''
        if self.on_hold: held_msg = _(' - On Hold')
        dep_msg = ''
        if self.can_be_resolved == False: dep_msg = _(' - Open dependencies')
        return u'%s%s%s' % (self.get_status_display(), held_msg, dep_msg)
    get_status = property(_get_status)

    def _get_ticket_url(self):
        """
        Returns a publicly-viewable URL for this ticket, used when giving
        a URL to the submitter of a ticket.
        """
        from django.contrib.sites.models import Site
        from django.core.urlresolvers import reverse
        try:
            site = Site.objects.get_current()
        except:
            site = Site(domain='configure-django-sites.com')
        return "https://dataglen.com/solar/plant/" + self.queue.plant.slug + "/ticket_view/" + str(self.id) + "/"
    ticket_url = property(_get_ticket_url)

    def _get_staff_url(self):
        """
        Returns a staff-only URL for this ticket, used when giving a URL to
        a staff member (in emails etc)
        """
        from django.contrib.sites.models import Site
        from django.core.urlresolvers import reverse
        try:
            site = Site.objects.get_current()
        except:
            site = Site(domain='configure-django-sites.com')
        return u"http://%s%s" % (
            site.domain,
            reverse('helpdesk_view',
            args=[self.id])
            )
    staff_url = property(_get_staff_url)

    def _can_be_resolved(self):
        """
        Returns a boolean.
        True = any dependencies are resolved
        False = There are non-resolved dependencies
        """
        OPEN_STATUSES = (Ticket.OPEN_STATUS, Ticket.REOPENED_STATUS)
        return TicketDependency.objects.filter(ticket=self).filter(depends_on__status__in=OPEN_STATUSES).count() == 0
    can_be_resolved = property(_can_be_resolved)

    class Meta:
        get_latest_by = "created"
        ordering = ('id',)
        verbose_name = _('Ticket')
        verbose_name_plural = _('Tickets')

    def __str__(self):
        return '%s %s' % (self.id, self.title)

    def get_absolute_url(self):
        return ('helpdesk_view', (self.id,))
    get_absolute_url = models.permalink(get_absolute_url)

    def save(self, *args, **kwargs):
        if not self.id:
            existing_ticket = self.queue.ticket.filter(event_type=self.event_type).exclude(status=4)
            if len(existing_ticket) > 0:
                raise ValidationError(_("There is already an open ticket of this type. "
                                        "Please add new associations there."))
            # This is a new ticket as no ID yet exists.
            self.created = timezone.now()

        if not self.priority:
            self.priority = 3

        self.modified = timezone.now()
        super(Ticket, self).save(*args, **kwargs)

    # event that has occurred - causing the creation of this ticket
    event_type = models.CharField(choices=EVENT_TYPE, max_length=50, blank=False, null=False, db_index=True)
    # energy loss that happened - will be calculated when ticket gets closed
    energy_loss = models.FloatField(blank=True, null=True)
    # probable or definite cause behind energy loss
    energy_loss_cause = models.CharField(choices=ENERGY_LOSS_CAUSE, max_length=50, blank=True, null=True)
    # expected energy
    expected_energy = models.FloatField(blank=True, null=True)
    # actual energy
    actual_energy = models.FloatField(blank=True, null=True)

    # add a new ticket association
    def _add_ticket_association(self, identifier, created_ts=None):
        if created_ts is None:
            created_ts = timezone.now()
        try:
            sensor = Sensor.objects.get(sourceKey=identifier)

            identifier_name = sensor.name
            if "DISCONNECTED" in self.event_type:
                last_data_write_ts = sensor.get_last_write_ts()
                if last_data_write_ts is not None:
                    created_ts = last_data_write_ts
                else:
                    created_ts = created_ts - timedelta(seconds=int(sensor.timeoutInterval))
        except Sensor.DoesNotExist:
            # will associations be with Sensor's child always?
            logger.debug("this device has no name")
            return False

        # TODO reconsider for DATA_ANALYTICS
        try:
            # save a new association if we've reached this far
            logger.debug("tac: %s %s %s %s %s" % (self.id, self.event_type, identifier, identifier_name, created_ts))
            ta = TicketAssociation.objects.create(ticket=self,
                                                  event_type=self.event_type,
                                                  identifier=identifier,
                                                  identifier_name=identifier_name,
                                                  created=created_ts,
                                                  active=True)
            #ta.save()
            return ta
        except Exception as exc:
            logger.debug("Error creating a new association" + str(exc))
            return False

    # update a ticket association
    def _update_ticket_association(self, identifier, updated_ts=None):
        if updated_ts is None:
            updated_ts = timezone.now()
        try:
            association = self.associations.get(identifier=identifier, active=True)
            association.updated = updated_ts
            association.save()
            return True
        except Exception as exc:
            print ",".join([str(self.id), str(identifier), str(updated_ts)])
            print("error updating association: ", str(exc))
            return False

    # close a ticket association
    def _close_ticket_association(self, identifier, closed_ts=None):
        if closed_ts is None:
            closed_ts = timezone.now()
        try:
            association = self.associations.get(identifier=identifier, active=True)
            # close alarm associations
            for alarm in association.alarms.filter(active=True):
                alarm.close(closed_ts)
            # assert that no AnalyticsAssociations are open
            assert (len(association.performance_associations.filter(active=True)) == 0)
            # assert that no AlarmAssociation are open
            assert (len(association.alarms.filter(active=True)) == 0)
            # close this associations
            association.close(closed_ts)

            try:
                # logger.debug("scheduling an offline job - to be processed after 15 mins")
                analyse_association.apply_async(args=[association.id], countdown=60*30)
            except Exception as exc:
                logger.debug("error scheduling an offline job: " + str(exc))
                pass

            return True
        except AssertionError as exc:
            # logger.debug("open performance analytics associations for this association: " + str(exc))
            return False
        except Exception as exc:
            logger.debug("error closing a ticket association: " + str(exc))
            return False

    # update all ticket associations - only where associations can be more than 1.
    # ['asdasd,'asdasdasd'] {'asdasd':[104,105], 'asdasdasd':[103,106]}
    def update_ticket_associations(self, identifiers_list,
                                   alarms_dict=None,
                                   performance_dict=None,
                                   alarms_disabled=False,
                                   updated_at=None):
        try:
            from dgusers.models import UserRole
            if updated_at is None:
                updated_at = timezone.now()

            try:
                assert(len(identifiers_list) == len(set(identifiers_list)))
            except AssertionError:
                logger.debug(",".join([str(self.id), "identifiers list has duplicates: ", str(identifiers_list)]))
                pass

            if self.event_type == "GATEWAY_POWER_OFF" \
                    or self.event_type == "GATEWAY_DISCONNECTED" \
                    or self.event_type == "INVERTERS_DISCONNECTED" \
                    or self.event_type == "AJBS_DISCONNECTED" \
                    or self.event_type == "INVERTERS_NOT_GENERATING":
                try:
                    assert(alarms_dict is None)
                    assert(performance_dict is None)
                except AssertionError:
                    logger.debug("alarms/performance dict not accepted for this operation on this ticket type" + str(self.id) + str(alarms_dict) + str(performance_dict))


                # get all ACTIVE associations for this ticket
                existing_identifiers = [str(x[0]) for x in self.associations.filter(active=True).values_list('identifier')]
                # new list of associations
                new_identifiers = identifiers_list

                logger.debug("tk_id, %s ,existing_identifiers %s" % (self.id, existing_identifiers))
                logger.debug("tk_id, %s ,new_identifiers %s" % (self.id, new_identifiers))

                to_be_closed = set(existing_identifiers).difference(new_identifiers)
                logger.debug("tk_id, %s , to_be_closed %s" % (self.id, to_be_closed))

                to_be_created = set(new_identifiers).difference(existing_identifiers)
                logger.debug("tk_id, %s , to_be_created %s" % (self.id, to_be_created))

                to_be_updated = set(existing_identifiers).intersection(new_identifiers)
                logger.debug("tk_id, %s , to_be_updated %s" % (self.id, to_be_updated))

                for identifier in to_be_closed:
                    self._close_ticket_association(identifier, updated_at)
                for identifier in to_be_updated:
                    self._update_ticket_association(identifier, updated_at)
                for identifier in to_be_created:
                    self._add_ticket_association(identifier, updated_at)

                try:
                    if len(to_be_created) > 0 :
                        event_desc, pre_header, impacted_devices_description, impacted_devices_list, sms_text = prepare_descriptions(to_be_created, self.event_type, self.queue.plant)
                        # logger.debug(",".join(["Descriptions :Ticket ID (to_be_created)", str(self.id), str(self.queue.plant.slug),
                        #                        str(event_desc), str(impacted_devices_list), str(sms_text)]))
                        if pre_header is not None and impacted_devices_description is not None and impacted_devices_description is not None:
                            emails_list, phone_numbers_list = UserRole.users_list_for_notifications(self.queue.plant.slug, self.event_type, closing_alert=False)
                            # logger.debug(",".join(["Ticket ID (to_be_created)", str(self.id), str(self.queue.plant.slug), str(self.event_type), str(emails_list), str(phone_numbers_list)]))
                            for email in emails_list:
                                # send notification
                                send_new_alarm(self.id, self.queue.plant.name, pre_header, self.queue.plant.groupClient.name,
                                               impacted_devices_description, impacted_devices_list, self._get_ticket_url(),
                                               event_desc, "support@dataglen.com", email, logger)
                            for phone_number in phone_numbers_list:
                                send_infini_sms(phone_number, sms_text)

                    if len(to_be_closed) > 0:
                        event_desc, pre_header, impacted_devices_description, impacted_devices_list, sms_text = prepare_descriptions_close(to_be_closed, self.event_type, self.queue.plant)
                        # logger.debug(",".join(["Descriptions :Ticket ID (to_be_closed)", str(self.id), str(self.queue.plant.slug),
                        #                        str(event_desc), str(impacted_devices_list), str(sms_text)]))
                        emails_list, phone_numbers_list = UserRole.users_list_for_notifications(self.queue.plant.slug,
                                                                                       self.event_type, closing_alert=True)
                        # logger.debug(",".join(["Ticket ID (to_be_closed)", str(self.id), str(self.queue.plant.slug),
                        #                        str(self.event_type), str(emails_list), str(phone_numbers_list)]))
                        for email in emails_list:
                            send_close_alarm(self.id, self.queue.plant.name, pre_header, self.queue.plant.groupClient.name,
                                             impacted_devices_description, impacted_devices_list, self._get_ticket_url(),
                                             event_desc, "support@dataglen.com", email, logger)
                        for phone_number in phone_numbers_list:
                            send_infini_sms(phone_number, sms_text, new_alarm=False)
                        # if self.queue.plant.groupClient.name == "Renew Power":
                        #     send_close_alarm(self.id, self.queue.plant.name, pre_header,
                        #                      self.queue.plant.groupClient.name,
                        #                      impacted_devices_description, impacted_devices_list,
                        #                      self._get_ticket_url(),
                        #                      event_desc, "support@dataglen.com", "p.abhishek@renewpower.in", logger)

                except Exception as exc:
                    logger.debug(str(exc))
                    pass

            # pass a list of identifiers and a dict with key as an identifier and a list with error codes
            elif self.event_type == "INVERTERS_ALARMS" or self.event_type == "AJB_STRING_CURRENT_ZERO_ALARM":
                try:
                    assert(alarms_dict is not None)
                    assert(performance_dict is None)
                    if len(identifiers_list) > 0:
                        for key in alarms_dict.keys():
                            assert(alarms_dict[key].get('solar_status', None) is not None)
                except AssertionError:
                    raise ValidationError("Either alarm_dict is not passed, performance dict is passed, "
                                          "or solar status is not mentioned")
                # get all ACTIVE associations for this ticket
                #existing_identifiers = self.associations.filter(active=True).values_list('identifier')
                existing_identifiers_values = self.associations.filter(active=True).values_list('identifier')
                existing_identifiers = [item[0] for item in existing_identifiers_values]
                new_identifiers = identifiers_list

                to_be_closed = set(existing_identifiers).difference(new_identifiers)
                to_be_created = set(new_identifiers).difference(existing_identifiers)
                to_be_updated = set(existing_identifiers).intersection(new_identifiers)

                logger.debug("tk_id, %s ,existing_identifiers%s" % (self.id, existing_identifiers))
                logger.debug("tk_id, %s ,new_identifiers%s" % (self.id, new_identifiers))
                logger.debug("tk_id, %s , to_be_closed%s" % (self.id, to_be_closed))
                logger.debug("tk_id, %s , to_be_created%s" % (self.id, to_be_created))
                logger.debug("tk_id, %s , to_be_updated%s" % (self.id, to_be_updated))

                alarms_descriptions = []
                for identifier in to_be_updated:
                    ta = self.associations.get(identifier=identifier, active=True)
                    ta.update_alarm_associations(solar_status=alarms_dict[identifier]['solar_status'],
                                                 alarms_code_list=alarms_dict[identifier]['alarm_codes'],
                                                 alarms_disabled=alarms_disabled,
                                                 updated_at=updated_at)
                    self._update_ticket_association(identifier, updated_at)
                for identifier in to_be_created:
                    ta = self._add_ticket_association(identifier, updated_at)
                    ta.update_alarm_associations(solar_status=alarms_dict[identifier]['solar_status'],
                                                 alarms_code_list=alarms_dict[identifier]['alarm_codes'],
                                                 alarms_disabled=alarms_disabled,
                                                 updated_at=updated_at)
                    try:
                        if self.event_type == "INVERTERS_ALARMS":
                            try:
                                solar_status_description = get_solar_status_code_mapping(identifier, str(
                                    alarms_dict[identifier]['solar_status']))
                            except Exception as exc:
                                print exc
                                solar_status_description = str(alarms_dict[identifier]['solar_status'])

                            if len(alarms_dict[identifier]['alarm_codes']) > 0:
                                try:
                                    alarms_description = get_alarm_code_name(identifier, alarms_dict[identifier]['alarm_codes'][0])
                                except Exception as exc:
                                    print exc
                                    alarms_description = str(alarms_dict[identifier]['alarm_codes'][0])

                                alarms_descriptions.append("/".join([Sensor.objects.get(sourceKey=identifier).name,
                                                                     "STATUS:" + solar_status_description,
                                                                     "ALARM: " + alarms_description]))

                            else:
                                alarms_descriptions.append("/".join([Sensor.objects.get(sourceKey=identifier).name,
                                                                     "STATUS:" + solar_status_description]))

                        else:
                            alarms_descriptions.append("/".join([Sensor.objects.get(sourceKey=identifier).name,
                                                                 "STRINGS: " + ",".join(alarms_dict[identifier]['alarm_codes'])]))

                    except:
                        continue
                for identifier in to_be_closed:
                    # there is no need for this, as _close_ticket_association will close all
                    # open alarm_associations with this identifier

                    # ta = self.associations.get(identifier=identifier, active=True)
                    # solar_status=alarms_dict[identifier]['solar_status']
                    # ta.update_alarm_associations(solar_status=solar_status,
                    #                              alarms_code_list=[],
                    #                              updated_at=updated_at)
                    self._close_ticket_association(identifier, updated_at)

                try:
                    if len(to_be_created) > 0 :
                        # logger.debug(alarms_descriptions)
                        event_desc, pre_header, impacted_devices_description, impacted_devices_list, sms_text = prepare_descriptions(to_be_created,
                                                                                                                                     self.event_type,
                                                                                                                                     self.queue.plant,
                                                                                                                                     alarms_descriptions=alarms_descriptions)
                        # logger.debug(",".join(["Descriptions :Ticket ID (to_be_created)", str(self.id), str(self.queue.plant.slug),
                        #                        str(event_desc), str(impacted_devices_list), str(sms_text)]))
                        if pre_header is not None and impacted_devices_description is not None and impacted_devices_description is not None:
                            emails_list, phone_numbers_list = UserRole.users_list_for_notifications(self.queue.plant.slug, self.event_type, closing_alert=False)
                            # logger.debug(",".join(["Ticket ID (to_be_created)", str(self.id), str(self.queue.plant.slug), str(self.event_type), str(emails_list), str(phone_numbers_list)]))
                            for email in emails_list:
                                # send notification
                                send_new_alarm(self.id, self.queue.plant.name, pre_header, self.queue.plant.groupClient.name,
                                               impacted_devices_description, impacted_devices_list, self._get_ticket_url(),
                                               event_desc, "support@dataglen.com", email, logger)
                            for phone_number in phone_numbers_list:
                                send_infini_sms(phone_number, sms_text)
                    if len(to_be_closed) > 0:
                        event_desc, pre_header, impacted_devices_description, impacted_devices_list, sms_text = prepare_descriptions_close(to_be_closed, self.event_type, self.queue.plant)
                        # logger.debug(",".join(["Descriptions :Ticket ID (to_be_closed)", str(self.id), str(self.queue.plant.slug),
                        #                        str(event_desc), str(impacted_devices_list), str(sms_text)]))
                        emails_list, phone_numbers_list = UserRole.users_list_for_notifications(self.queue.plant.slug,
                                                                                       self.event_type, closing_alert=True)
                        # logger.debug(",".join(["Ticket ID (to_be_closed)", str(self.id), str(self.queue.plant.slug),
                        #                        str(self.event_type), str(emails_list), str(phone_numbers_list)]))
                        for email in emails_list:
                            send_close_alarm(self.id, self.queue.plant.name, pre_header, self.queue.plant.groupClient.name,
                                             impacted_devices_description, impacted_devices_list, self._get_ticket_url(),
                                             event_desc, "support@dataglen.com", email, logger)
                        for phone_number in phone_numbers_list:
                            send_infini_sms(phone_number, sms_text, new_alarm=False)
                except Exception as exc:
                    logger.debug(str(exc))
                    pass

            elif self.event_type == "INVERTERS_UNDERPERFORMING" or \
                    self.event_type == "MPPT_UNDERPERFORMING" or \
                    self.event_type == "AJB_UNDERPERFORMING" or \
                    self.event_type == "PANEL_CLEANING":
                try:
                    assert(alarms_dict is None)
                    assert(performance_dict is not None)
                except AssertionError:
                    raise ValidationError("Either alarm_dict is  passed, or performance_dict is NOT passed")
                existing_identifiers_values = self.associations.filter(active=True).values_list('identifier')
                existing_identifiers = [item[0] for item in existing_identifiers_values]
                new_identifiers = identifiers_list

                to_be_closed = set(existing_identifiers).difference(new_identifiers)
                to_be_created = set(new_identifiers).difference(existing_identifiers)
                to_be_updated = set(existing_identifiers).intersection(new_identifiers)

                # associations to be created
                for identifier in to_be_created:
                    ta = self._add_ticket_association(identifier, updated_at)
                    ta.create_performance_associations(performance_dict[identifier],
                                                       updated_at)
                for identifier in to_be_closed:
                    self._close_ticket_association(identifier, updated_at)

                for identifier in to_be_updated:
                    ta = self.associations.get(identifier=identifier, active=True)
                    ta.create_performance_associations(performance_dict[identifier],
                                                       updated_at)
                    # update the ticket association
                    self._update_ticket_association(identifier, updated_at)
        except Exception as exception:
            print ",".join([str(self.id), str(identifiers_list), str(alarms_dict), str(performance_dict),
                            str(alarms_disabled), str(updated_at)])
            print("Error in updating associations : " + str(exception))

    @staticmethod
    # return the number of Critical, High, Normal, Low, Very Low
    def get_plant_live_priority_summary(plant):
        data = {'CRITICAL': 0, 'HIGH': 0, 'NORMAL': 0}
        for queue in plant.queues.all():
            tickets = queue.ticket.filter(status__in=[1, 2, 3, 6])
            for ticket in tickets:
                try:
                    # holds one ticket of each type per plant rule
                    if ticket.priority == 1:
                        data['CRITICAL'] += 1
                    elif ticket.priority == 2:
                        data['HIGH'] += 1
                    elif ticket.priority in [3,4,5]:
                        data['NORMAL'] += 1
                except Exception as exc:
                    logger.debug(str(exc))
                    continue
        return data

    @staticmethod
    def get_plant_live_ops_summary(plant, event_types = None):
        data = {}
        for queue in plant.queues.all():
            tickets = queue.ticket.filter(status__in=[1, 2, 3, 6])
            for ticket in tickets:
                try:
                    if event_types and ticket.event_type not in event_types:
                        continue
                    # holds one ticket of each type per plant rule
                    assert(ticket.event_type != data.keys())
                except AssertionError as exc:
                    logger.debug("There's more than 1 active ticket of same type")
                    return False
                data[ticket.event_type] = ticket.get_ticket_stats(True)
        return data

    def get_ticket_stats(self, active):
        # find active associations
        try:
            if "UNDERPERFOMING" in self.event_type or self.event_type == "PANEL_CLEANING":
                associations = self.associations.all()
            else:
                associations = self.associations.filter(active=active)
            data = {}
            total_associations = 0
            total_alarms = 0
            total_pa = 0
            for association in associations:
                try:
                    data[association.identifier_name]["associations"] += 1
                    data[association.identifier_name]["alarms"] += len(association.alarms.filter(active=active))
                    # since these will always be closed
                    data[association.identifier_name]["performance_issues"] += len(association.performance_associations.all())
                except KeyError:
                    data[association.identifier_name] = {}
                    data[association.identifier_name]["associations"] = 1
                    data[association.identifier_name]["alarms"] = len(association.alarms.filter(active=active))
                    data[association.identifier_name]["performance_issues"] = len(association.performance_associations.all())
                except Exception as exc:
                    logger.debug(
                        "Error while collecting ticket summary: " + str(exc)
                    )
                    continue
                total_associations += 1
                total_alarms += len(association.alarms.filter(active=active))
                total_pa += len(association.performance_associations.all())

            return {"details": data,
                    "total_associations": total_associations,
                    "total_alarms": total_alarms,
                    "ticket_id": self.id,
                    "total_performance_associations": total_pa}

        except Exception as exc:
            logger.debug("Error while collecting ticket summary: " + str(exc))
            return False

    # list of associations with the given active status for a ticket
    def get_devices_association_report(self, st, active, et=None, identifier = None):
        if identifier:
            if et is None:
                associations = self.associations.filter(created__gte=st,
                                                        active=active,
                                                        identifier=identifier)
            else:
                associations = self.associations.filter(created__gte=st,
                                                        created__lte=et,
                                                        active=active,
                                                        identifier=identifier)

        else:
            if et is None:
                associations = self.associations.filter(created__gte=st,
                                                        active=active)
            else:
                associations = self.associations.filter(created__gte=st,
                                                        created__lte=et,
                                                        active=active)

        data = {}
        # iterate through associations
        for association in associations:
            # store data in this dictionary - key will be alarm code
            alarms = {}
            performance_issues = {}
            # if there are alarms associated, pick them up.
            if self.event_type == 'INVERTERS_ALARMS' or self.event_type == "AJB_STRING_CURRENT_ZERO_ALARM":
                # get all the alarms
                alarm_associations = association.alarms.all()
                for aa in alarm_associations:
                    # data for this alarm
                    td = aa.closed - aa.created
                    aa_dict = {'alarm_created': aa.created, 'alarm_updated': aa.updated,
                               'alarm_closed': aa.closed, 'alarm_active_status': aa.active,
                               'alarm_duration_seconds': td.total_seconds(), 'alarm_code': aa.alarm_code,
                               'device_status': aa.identifier, 'alarm_id': aa.id}
                    try:
                        # store
                        alarms[aa.identifier].append(aa_dict)
                    except KeyError:
                        alarms[aa.identifier] = [aa_dict]
            elif self.event_type == "INVERTERS_UNDERPERFORMING" or \
                 self.event_type == "MPPT_UNDERPERFORMING" or \
                 self.event_type == "AJB_UNDERPERFORMING" or \
                 self.event_type == "PANEL_CLEANING":
                performance_associations = association.performance_associations.all()
                for pa in performance_associations:
                    pa_dict = {'performance_issue_created': pa.created, 'performance_issue_updated': pa.updated,
                               'performance_issue_closed': pa.closed, 'performance_issue_active_status': pa.active,
                               'performance_issue_device_name': pa.identifier,'delta_energy':pa.delta_energy,
                               'delta_current':pa.delta_current,'actual_power':pa.actual_power,'mean_power':pa.mean_power,
                               'delta_power':pa.delta_power,'mean_energy':pa.mean_energy,'mean_current':pa.mean_current,
                               'actual_energy':pa.actual_energy,'expected_energy':pa.expected_energy,'actual_current':pa.actual_current,
                               'residual':pa.residual,'mean_voltage':pa.mean_voltage}
                    try:
                        performance_issues[pa.identifier].append(pa_dict)
                    except KeyError:
                        performance_issues[pa.identifier] = [pa_dict]

            atd = association.closed - association.created
                # store data in this dictionary - identifier will be the key
            association_dict = {"association_ticket_id": association.ticket.id, "association_event_type": association.ticket.event_type,
                                'association_alarms': alarms, 'association_performance_issues': performance_issues,
                                'association_identifier_name': association.identifier_name,
                                'association_duration_seconds': atd.total_seconds(),
                                'association_created': association.created, 'association_updated': association.updated,
                                'association_closed': association.closed, 'association_active_status': association.active}

            try:
                data[association.identifier].append(association_dict)
            except KeyError:
                data[association.identifier] = [association_dict]

        return data

    #def get_ticket_energy_loss(self, st, et):

    def get_ticket_full_report(self, st, et, identifier = None):
        ticket_info = {}
        ticket_info['ticket_id'] = self.id
        try:
            ticket_info['ticket_status'] = Ticket.STATUS_CHOICES[int(self.status)-1][1].upper()
        except:
            ticket_info['ticket_status'] = "UNKNOWN"

        if self.actual_energy:
            ticket_info['actual_energy'] = self.actual_energy
        if self.expected_energy:
            ticket_info['expected_energy'] = self.expected_energy

        data_active = self.get_devices_association_report(st, True, et, identifier)
        data_inactive = self.get_devices_association_report(st, False, et, identifier)
        ticket_info['active_associations'] = data_active
        ticket_info['inactive_associations'] = data_inactive
        return ticket_info

    @staticmethod
    def get_plant_ticket_history(plant, st, et, event_types = None, identifier = None):
        data = {}
        for queue in plant.queues.all():
            tickets = queue.ticket.filter(created__gte=st, created__lte=et)
            for ticket in tickets:
                if event_types and ticket.event_type not in event_types:
                    continue
                else:
                    try:
                        data[ticket.event_type].append(ticket.get_ticket_full_report(st, et, identifier))
                    except:
                        data[ticket.event_type] = [ticket.get_ticket_full_report(st, et, identifier)]
        return data

    @staticmethod
    def get_device_ticket_history(plant, st, et, identifier, event_types = None):
        data = []
        for queue in plant.queues.all():
            if event_types is None:
                tickets = queue.ticket.filter(created__gte=st, created__lte=et)
            else :
                tickets = queue.ticket.filter(created__gte=st, created__lte=et, event_type__in = event_types)
            for ticket in tickets:
                try:
                    try:
                        # get all active associations for this devices and ticket
                        data = data + ticket.get_devices_association_report(st, True, et, identifier)[identifier]
                    except KeyError:
                        pass
                    try:
                        # get all inactive associations for this devices and ticket
                        data = data + ticket.get_devices_association_report(st, False, et, identifier)[identifier]
                    except KeyError:
                        pass
                except:
                    continue
        return data

    @staticmethod
    def get_identifier_history(plant, st, et, identifier, event_types = None):
        try:
            assert(identifier is not None)
        except:
            raise ValidationError("Identifiers cannot be an empty list")

        try:
            data = Ticket.get_device_ticket_history(plant, st, et, identifier, event_types)
        except:
            return {}
        return data

class TicketAssociation(models.Model):
    ticket = models.ForeignKey(Ticket, related_name="associations",
                               related_query_name="associations")
    # associated device
    identifier = models.CharField(max_length=200, blank=False, null=False, db_index=True)
    # identifier name
    identifier_name = models.CharField(max_length=200, blank=True, null=True)
    # the type of event
    event_type = models.CharField(choices=EVENT_TYPE, max_length=50, blank=False, null=False, db_index=True)
    # created at
    created = models.DateTimeField(blank=False, null=False, help_text="Time at which this association was created", db_index=True)
    # updated_at
    updated = models.DateTimeField(blank=True, null=True, db_index=True)
    # energy loss that happened - will be calculated when ticket gets closed
    energy_loss = models.FloatField(blank=True, null=True)
    # probable or definite cause behind energy loss
    energy_loss_cause = models.CharField(choices=ENERGY_LOSS_CAUSE, max_length=50, blank=True, null=True)
    # expected energy
    expected_energy = models.FloatField(blank=True, null=True)
    # actual energy
    actual_energy = models.FloatField(blank=True, null=True)

    closed = models.DateTimeField(blank=True, null=True, db_index=True)
    active = models.BooleanField(default=True, blank=False)

    def save(self, *args, **kwargs):
        # if it's a new association with active set to True
        if not self.pk and self.active is True:
            existing_active_associations = self.ticket.associations.filter(identifier=self.identifier,
                                                                           event_type=self.event_type,
                                                                           active=True)
            if len(existing_active_associations) > 0:
                raise ValidationError(_(",".join(["consistency error, active association already exists ",
                                                  str(self.ticket),
                                                  str(self.ticket.queue.plant.slug),
                                                  str(timezone.now()),
                                                  str(self.identifier),
                                                  str(self.event_type),
                                                  str(self.active)])))

        # all good
        super(TicketAssociation, self).save(*args, **kwargs)

    def close(self, closed_at):
        self.active = False
        self.closed = closed_at
        self.save()

    # add a new alarm association
    def _add_alarm_association(self, device_status_number,
                               created_at,
                               alarm_code=None,
                               alarm_description=None,
                               alarm_resolution=None,
                               device_status_description=None):

        if created_at is None:
            created_at = timezone.now()


        try:
            # assert that device status is not None, while alarm_code can be
            assert (device_status_number is not None)

            try:
                if device_status_description is None:
                    inverter_status_mapping = InverterStatusMappings.objects.get(plant=self.ticket.queue.plant,
                                                                                 stream_name='SOLAR_STATUS',
                                                                                 status_code=float(
                                                                                 device_status_number))

                    device_status_description = inverter_status_mapping.status_description
            except Exception as exc:
                logger.debug(",".join([str(exc), str(self.ticket.queue.plant.slug), str(device_status_number)]))
                if self.ticket.event_type == "AJB_STRING_CURRENT_ZERO_ALARM":
                    device_status_description = "AJBs current dropped to zero"
                else:
                    device_status_description = "No description available"

            try:
                if alarm_description is None and self.ticket.event_type == "INVERTERS_ALARMS":
                    inv = IndependentInverter.objects.get(sourceKey=self.identifier)
                    inv_error_codes = InverterErrorCodes.objects.filter(manufacturer=inv.manufacturer.upper(), error_code=alarm_code)
                    alarm_description = inv_error_codes[0].error_description
            except:
                alarm_description = "No error details available"

            if self.ticket.event_type == "INVERTERS_ALARMS" or self.ticket.event_type == "AJB_STRING_CURRENT_ZERO_ALARM":
                try:
                    ea = AlarmAssociation(ticket_association=self,
                                          identifier=device_status_number,
                                          device_status_number=device_status_number,
                                          alarm_code=alarm_code,
                                          alarm_description=alarm_description,
                                          alarm_resolution=alarm_resolution,
                                          device_status_description=device_status_description,
                                          created=created_at,
                                          active=True)
                    ea.save()
                    return True
                except Exception as exc:
                    logger.debug("error creating a new alarmassociation: " + str(exc))
            else:
                logger.debug("alarms/events not allowed for such a ticket")
                return False
        except Exception as exc:
            print("there's an error saving a new event association", str(exc))
            return False

    # update an alarm association
    def _update_alarm_association(self,
                                  device_status_number,
                                  updated_at,
                                  alarm_code=None,
                                  alarm_description=None):
        if updated_at is None:
            updated_at = timezone.now()
        try:
            # assert that device status is not None, while alarm_code can be
            assert (device_status_number is not None)

            # get an event association
            if alarm_code is not None:
                ea = self.alarms.get(device_status_number=device_status_number,
                                     alarm_code=alarm_code,
                                     active=True)
            else:
                ea = self.alarms.get(device_status_number=device_status_number,
                                     active=True)

            assert (float(ea.device_status_number) == float(device_status_number))

            ea.updated = updated_at

            if alarm_description:
                ea.alarms_description = alarm_description

            ea.save()
        except Exception as exc:
            logger.debug("problem updating event association %s ticket %s" % (self.id, exc))
            return False

    # close an active alarm
    def _close_alarm_association(self,
                                 device_status_number,
                                 closed_at,
                                 alarm_code=None):
        if closed_at is None:
            closed_at = timezone.now()
        try:
            assert(device_status_number is not None)
            # get an event association
            if alarm_code is not None:
                ea = self.alarms.get(device_status_number = device_status_number,
                                 alarm_code=alarm_code, active=True)
            else :
                ea = self.alarms.get(device_status_number = device_status_number,
                                     active = True)

            assert (ea.device_status_number == device_status_number)
            ea.close(closed_at)
        except Exception as exc:
            print("there's a problem closing the event association:" + str(exc))
            return False

    # update alarms associations
    def update_alarm_associations(self, solar_status,
                                  alarms_code_list,
                                  alarms_disabled=False,
                                  updated_at=None):
        # logger.debug("update_alarm_association")
        # logger.debug(solar_status)
        # logger.debug(alarms_code_list)
        # logger.debug(alarms_disabled)
        association_with_no_alarm_exists = False

        if updated_at is None:
            updated_at = timezone.now()
        try:
            # solar status has to be there
            assert(solar_status is not None)
            # there can only be one maximum alarm
            #assert(len(alarms_code_list) <= 1)
            # no_alarms cannot be True if there are alarms
            if alarms_disabled is True:
                assert(len(alarms_code_list) == 0)

            # 4 steps
            # (1) first close alarms where association is not solar_status - if there's a change in the solar status
            existing_not_solar_status = self.alarms.filter(~Q(identifier=solar_status),
                                                           active=True)
            for item in existing_not_solar_status:
                item.close(closed_at=updated_at)

            # (2) now focus on alarms which are related with the passed solar_status
            existing_alarms = []
            existing_alarms_values = self.alarms.filter(identifier=solar_status,
                                                        active=True)
            # logger.debug(existing_alarms_values)

            # (3) update alarms which have no alarm_code
            for item in existing_alarms_values:
                if item.alarm_code is None:
                    association_with_no_alarm_exists = True
                    self._update_alarm_association(solar_status,
                                                   updated_at=updated_at)
                else:
                    existing_alarms.append(item.alarm_code)

            # (4) now update/close/create alarms where alarm_code is specified for the given solar status
            new_alarms = alarms_code_list
            to_be_created = set(new_alarms).difference(existing_alarms)
            to_be_closed = set(existing_alarms).difference(new_alarms)
            to_be_updated = set(existing_alarms).intersection(new_alarms)
            # logger.debug(to_be_created)
            # logger.debug(to_be_closed)
            # logger.debug(to_be_updated)
            for alarm_code in to_be_created:
                self._add_alarm_association(device_status_number=solar_status,
                                            alarm_code=alarm_code,
                                            created_at=updated_at)
            for alarm_code in to_be_closed:
                self._close_alarm_association(device_status_number=solar_status,
                                              alarm_code=alarm_code,
                                              closed_at=updated_at)
            for alarm_code in to_be_updated:
                self._update_alarm_association(device_status_number=solar_status,
                                               alarm_code=alarm_code,
                                               updated_at=updated_at)

            # if there is no open ticket for the given solar status and no alarm code is mentioned
            if alarms_disabled is True and len(alarms_code_list) == 0 and association_with_no_alarm_exists == False:
                self._add_alarm_association(device_status_number=solar_status,
                                            created_at=updated_at)

            return True
        except AssertionError as exc:
            print("either solar status is none or alarm code list has more than 1 alarm code", str(exc))
            return False

        except Exception as exc:
            print("there's a problem updating event associations", str(exc))
            return False

    # add a new performance association
    def _create_and_close_performance_association(self, st, et, identifier,
                                                  created_at=None,
                                                  delta_energy=None, delta_current=None,
                                                  actual_power=None, mean_power=None, delta_power=None,
                                                  mean_energy=None, mean_current=None,
                                                  actual_energy=None, actual_current=None,
                                                  residual=None):
        if created_at is None:
            created_at = timezone.now()
        try:
            if self.ticket.event_type == "INVERTERS_UNDERPERFORMING" or \
               self.ticket.event_type == "MPPT_UNDERPERFORMING" or \
               self.ticket.event_type == "AJB_UNDERPERFORMING" or \
               self.ticket.event_type == "PANEL_CLEANING":
                    aa = AnalyticsAssociation(ticket_association=self,
                                              st=st, et=et, identifier=identifier,
                                              created=created_at,
                                              delta_energy=delta_energy, delta_current=delta_current,
                                              actual_power=actual_power, mean_power=mean_power, delta_power=delta_power,
                                              mean_energy=mean_energy, mean_current=mean_current,
                                              actual_energy=actual_energy, actual_current=actual_current,
                                              residual=residual, active=True)
                    aa.save()
                    # since this is a performance association - close it now
                    aa.closed = created_at
                    aa.active = False
                    aa.save()
                    return True
            else:
                logger.debug("analytics associations not allowed for such a ticket")
                return False
        except Exception as exc:
            print("there's an error saving a new analytics association", str(exc))
            return False

    def create_performance_associations(self, performance_dict_list, created_at):
        for pa in performance_dict_list:
            try:
                created = self._create_and_close_performance_association(pa['st'], pa['et'], pa['identifier'],
                                                                         created_at=created_at,
                                                                         delta_energy=pa.get('delta_energy', None),
                                                                         delta_current=pa.get('delta_current', None),
                                                                         actual_power=pa.get('actual_power', None),
                                                                         mean_power=pa.get('mean_power', None),
                                                                         delta_power=pa.get('delta_power', None),
                                                                         mean_energy=pa.get('mean_energy', None),
                                                                         mean_current=pa.get('mean_current', None),
                                                                         actual_energy=pa.get('actual_energy', None),
                                                                         actual_current=pa.get('actual_current', None),
                                                                         residual=pa.get('residual', None))
                if created:
                    print 'new pa created: ' + str(pa)
                    # logger.debug('new pa created: ' + str(pa))
                else:
                    logger.debug('error creating new pa: ' + str(pa))

            except KeyError as exc:
                logger.debug('key error in creating pa: ' + str(exc))
                continue

    def __unicode__(self):
        return "_".join([str(self.ticket.title), str(self.identifier_name), str(self.event_type)])


class BaseEventAssociation(models.Model):
    identifier = models.CharField(max_length=100, blank=False, null=False, db_index=True)
    # created at
    created = models.DateTimeField(blank=False, null=False, db_index=True, help_text="Time at which this association was created")
    # updated_at
    updated = models.DateTimeField(blank=True, null=True, db_index=True)
    # closed at
    closed = models.DateTimeField(blank=True, null=True, db_index=True)
    # active or not
    active = models.BooleanField(default=True, blank=False, db_index=True)
    # energy loss that happened - will be calculated when ticket gets closed
    energy_loss = models.FloatField(blank=True, null=True)
    # probable or definite cause behind energy loss
    energy_loss_cause = models.CharField(choices=ENERGY_LOSS_CAUSE, max_length=50, blank=True, null=True)

    def __unicode__(self):
        return "_".join([str(self.identifier), str(self.active)])


# this will be used for inverters and ajbs - need to check on alarm code and description before saving
class AlarmAssociation(BaseEventAssociation):
    # TODO add a unique for a combination of ticket_association and identifier
    ticket_association = models.ForeignKey(TicketAssociation, related_name="alarms",
                                           related_query_name="alarm")
    # solar status number
    device_status_number = models.FloatField(blank=False, null=False, help_text="solar status, cannot be None")
    # alarm code - unique
    alarm_code = models.CharField(max_length=20, blank=True, null=True, help_text="corresponding error code, optional")
    # alarm description
    alarm_description = models.CharField(max_length=1000, blank=True, null=True)
    # resolution
    alarm_resolution = models.CharField(max_length=1000, blank=True, null=True)
    # solar status description
    device_status_description = models.CharField(max_length=500, blank=True, null=True)
    # expected energy
    expected_energy = models.FloatField(blank=True, null=True)
    # actual energy
    actual_energy = models.FloatField(blank=True, null=True)

    def save(self, *args, **kwargs):
        # If it's a new association with active set to True
        if not self.pk and self.active is True:
            if self.alarm_code is not None:
                existing_active_alarms = self.ticket_association.alarms.filter(identifier=self.identifier,
                                                                               device_status_number=self.device_status_number,
                                                                               alarm_code=self.alarm_code,
                                                                               active=True)
            else:
                existing_active_alarms = self.ticket_association.alarms.filter(identifier=self.identifier,
                                                                               device_status_number=self.device_status_number,
                                                                               active=True)

            if len(existing_active_alarms) > 0:
                raise ValidationError(_(",".join(["consistency error, active alarm already exists ",
                                                  str(self.ticket_association),
                                                  str(self.ticket_association.ticket),
                                                  str(self.ticket_association.ticket.queue.plant.slug),
                                                  str(timezone.now()),
                                                  str(self.device_status_number),
                                                  str(self.alarm_code),
                                                  str(self.identifier),
                                                  str(self.active)])))
        # all good
        super(AlarmAssociation, self).save(*args, **kwargs)

    # close this association
    def close(self, closed_at):
        self.active = False
        self.closed = closed_at
        self.save()

    @staticmethod
    def _serialize(alarms):
        data = []
        for alarm in alarms:
            data.append({'created': alarm.created, 'closed': alarm.updated, 'ticket_id': alarm.ticket_association.id,
                         'alarm_code': alarm.alarm_code, 'alarm_description': alarm.alarm_description,
                         'alarm_resolution': alarm.alarm_resolution, 'energy_loss': alarm.energy_loss,
                         'energy_loss_cause': alarm.energy_loss_cause})
        return data

    @staticmethod
    def get_device_open_alarms(identifier):
        alarms = AlarmAssociation.objects.filter(identifier=identifier,
                                                 active=True)
        return AlarmAssociation._serialize(alarms)

    @staticmethod
    def get_device_historical_alarms(st, et, identifier, active=False):
        alarms = AlarmAssociation.objects.filter(identifier=identifier, created__gte=st,
                                                 closed__lte=et, active=active)
        return AlarmAssociation._serialize(alarms)


# analytics association
class AnalyticsAssociation(BaseEventAssociation):
    # TODO add a unique for a combination of ticket_association, and identifier
    ticket_association = models.ForeignKey(TicketAssociation,
                                           related_name="performance_associations",
                                           related_query_name="performance_association")
    st = models.DateTimeField(default=None, blank=False, null=False)
    et = models.DateTimeField(default=None, blank=False, null=False)
    delta_energy = models.FloatField(default=None, blank=True, null=True)
    delta_current = models.FloatField(default=None, blank=True, null=True)
    actual_power = models.FloatField(default=None, blank=True, null=True)
    mean_power = models.FloatField(default=None, blank=True, null=True)
    delta_power = models.FloatField(default=None, blank=True, null=True)
    mean_energy = models.FloatField(default=None, blank=True, null=True)
    mean_current = models.FloatField(default=None, blank=True, null=True)
    actual_energy = models.FloatField(default=None, blank=True, null=True)
    expected_energy = models.FloatField(default=None, blank=True, null=True)
    actual_current = models.FloatField(default=None, blank=True, null=True)
    residual = models.FloatField(default=None, blank=True, null=True)
    mean_voltage = models.FloatField(default=None, blank=True, null=True)

    @staticmethod
    def _serialize(performance_associations):
        data = []
        cumulative_energy_loss = 0.0
        for pa in performance_associations:
            data.append({'ticket_id': pa.ticket_association, 'st': pa.st, 'et': pa.et,
                         'delta_energy': pa.delta_energy, 'delta_current': pa.delta_current,
                         'actual_power': pa.actual_power, 'mean_power': pa.mean_power, 'delta_power': pa.delta_power,
                         'mean_energy': pa.mean_energy, 'mean_current': pa.mean_current,
                         'actual_energy': pa.actual_energy, 'actual_current': pa.actual_current})
            if pa.delta_energy is not None:
                cumulative_energy_loss += pa.delta_energy
        return data, cumulative_energy_loss

    @staticmethod
    def get_device_open_performance_tickets(identifier):
        pas = AnalyticsAssociation.objects.filter(identifier=identifier,
                                                  active=True)
        return AnalyticsAssociation._serialize(pas)

    @staticmethod
    def get_device_historical_performance_tickets(st, et, identifier, active=False):
        pas = AnalyticsAssociation.objects.filter(identifier=identifier, created__gte=st,
                                                  closed__lte=et, active=active)
        return AnalyticsAssociation._serialize(pas)


class FollowUpManager(models.Manager):
    def private_followups(self):
        return self.filter(public=False)

    def public_followups(self):
        return self.filter(public=True)


@python_2_unicode_compatible
class FollowUp(models.Model):
    """
    A FollowUp is a comment and/or change to a ticket. We keep a simple
    title, the comment entered by the user, and the new status of a ticket
    to enable easy flagging of details on the view-ticket page.

    The title is automatically generated at save-time, based on what action
    the user took.

    Tickets that aren't public are never shown to or e-mailed to the submitter,
    although all staff can see them.
    """

    ticket = models.ForeignKey(
        Ticket,
        verbose_name=_('Ticket'),
        )

    date = models.DateTimeField(
        _('Date'),
        default = timezone.now
        )

    title = models.CharField(
        _('Title'),
        max_length=200,
        blank=True,
        null=True,
        )

    comment = models.TextField(
        _('Comment'),
        blank=True,
        null=True,
        )

    public = models.BooleanField(
        _('Public'),
        blank=True,
        default=False,
        help_text=_('Public tickets are viewable by the submitter and all '
            'staff, but non-public tickets can only be seen by staff.'),
        )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        verbose_name=_('User'),
        )

    new_status = models.IntegerField(
        _('New Status'),
        choices=Ticket.STATUS_CHOICES,
        blank=True,
        null=True,
        help_text=_('If the status was changed, what was it changed to?'),
        )

    objects = FollowUpManager()

    class Meta:
        ordering = ['date']
        verbose_name = _('Follow-up')
        verbose_name_plural = _('Follow-ups')

    def __str__(self):
        return '%s' % self.title

    def get_absolute_url(self):
        return u"%s#followup%s" % (self.ticket.get_absolute_url(), self.id)

    def save(self, *args, **kwargs):
        t = self.ticket
        t.modified = timezone.now()
        t.save()
        super(FollowUp, self).save(*args, **kwargs)


@python_2_unicode_compatible
class TicketChange(models.Model):
    """
    For each FollowUp, any changes to the parent ticket (eg Title, Priority,
    etc) are tracked here for display purposes.
    """

    followup = models.ForeignKey(
        FollowUp,
        verbose_name=_('Follow-up'),
        )

    field = models.CharField(
        _('Field'),
        max_length=100,
        )

    old_value = models.TextField(
        _('Old Value'),
        blank=True,
        null=True,
        )

    new_value = models.TextField(
        _('New Value'),
        blank=True,
        null=True,
        )

    def __str__(self):
        out = '%s ' % self.field
        if not self.new_value:
            out += ugettext('removed')
        elif not self.old_value:
            out += ugettext('set to %s') % self.new_value
        else:
            out += ugettext('changed from "%(old_value)s" to "%(new_value)s"') % {
                'old_value': self.old_value,
                'new_value': self.new_value
                }
        return out

    class Meta:
        verbose_name = _('Ticket change')
        verbose_name_plural = _('Ticket changes')


def attachment_path(instance, filename):
    """
    Provide a file path that will help prevent files being overwritten, by
    putting attachments in a folder off attachments for ticket/followup_id/.
    """
    import os
    from django.conf import settings
    os.umask(0)
    path = 'helpdesk/attachments/%s/%s' % (instance.followup.ticket.ticket_for_url, instance.followup.id )
    att_path = os.path.join(settings.MEDIA_ROOT, path)
    if settings.DEFAULT_FILE_STORAGE == "django.core.files.storage.FileSystemStorage":
        if not os.path.exists(att_path):
            os.makedirs(att_path, 0o777)
    return os.path.join(path, filename)


@python_2_unicode_compatible
class Attachment(models.Model):
    """
    Represents a file attached to a follow-up. This could come from an e-mail
    attachment, or it could be uploaded via the web interface.
    """

    followup = models.ForeignKey(
        FollowUp,
        verbose_name=_('Follow-up'),
        )

    file = models.FileField(
        _('File'),
        upload_to=attachment_path,
        max_length=1000,
        )

    filename = models.CharField(
        _('Filename'),
        max_length=1000,
        )

    mime_type = models.CharField(
        _('MIME Type'),
        max_length=255,
        )

    size = models.IntegerField(
        _('Size'),
        help_text=_('Size of this file in bytes'),
        )

    def get_upload_to(self, field_attname):
        """ Get upload_to path specific to this item """
        if not self.id:
            return u''
        return u'helpdesk/attachments/%s/%s' % (
            self.followup.ticket.ticket_for_url,
            self.followup.id
            )

    def __str__(self):
        return '%s' % self.filename

    class Meta:
        ordering = ['filename',]
        verbose_name = _('Attachment')
        verbose_name_plural = _('Attachments')


@python_2_unicode_compatible
class PreSetReply(models.Model):
    """
    We can allow the admin to define a number of pre-set replies, used to
    simplify the sending of updates and resolutions. These are basically Django
    templates with a limited context - however if you wanted to get crafy it would
    be easy to write a reply that displays ALL updates in hierarchical order etc
    with use of for loops over {{ ticket.followup_set.all }} and friends.

    When replying to a ticket, the user can select any reply set for the current
    queue, and the body text is fetched via AJAX.
    """

    queues = models.ManyToManyField(
        Queue,
        blank=True,
        help_text=_('Leave blank to allow this reply to be used for all '
            'queues, or select those queues you wish to limit this reply to.'),
        )

    name = models.CharField(
        _('Name'),
        max_length=100,
        help_text=_('Only used to assist users with selecting a reply - not '
            'shown to the user.'),
        )

    body = models.TextField(
        _('Body'),
        help_text=_('Context available: {{ ticket }} - ticket object (eg '
            '{{ ticket.title }}); {{ queue }} - The queue; and {{ user }} '
            '- the current user.'),
        )

    class Meta:
        ordering = ['name',]
        verbose_name = _('Pre-set reply')
        verbose_name_plural = _('Pre-set replies')

    def __str__(self):
        return '%s' % self.name


@python_2_unicode_compatible
class EscalationExclusion(models.Model):
    """
    An 'EscalationExclusion' lets us define a date on which escalation should
    not happen, for example a weekend or public holiday.

    You may also have a queue that is only used on one day per week.

    To create these on a regular basis, check out the README file for an
    example cronjob that runs 'create_escalation_exclusions.py'.
    """

    queues = models.ManyToManyField(
        Queue,
        blank=True,
        help_text=_('Leave blank for this exclusion to be applied to all '
            'queues, or select those queues you wish to exclude with this '
            'entry.'),
        )

    name = models.CharField(
        _('Name'),
        max_length=100,
        )

    date = models.DateField(
        _('Date'),
        help_text=_('Date on which escalation should not happen'),
        )

    def __str__(self):
        return '%s' % self.name

    class Meta:
        verbose_name = _('Escalation exclusion')
        verbose_name_plural = _('Escalation exclusions')


@python_2_unicode_compatible
class EmailTemplate(models.Model):
    """
    Since these are more likely to be changed than other templates, we store
    them in the database.

    This means that an admin can change email templates without having to have
    access to the filesystem.
    """

    template_name = models.CharField(
        _('Template Name'),
        max_length=100,
        )

    subject = models.CharField(
        _('Subject'),
        max_length=100,
        help_text=_('This will be prefixed with "[ticket.ticket] ticket.title"'
            '. We recommend something simple such as "(Updated") or "(Closed)"'
            ' - the same context is available as in plain_text, below.'),
        )

    heading = models.CharField(
        _('Heading'),
        max_length=100,
        help_text=_('In HTML e-mails, this will be the heading at the top of '
            'the email - the same context is available as in plain_text, '
            'below.'),
        )

    plain_text = models.TextField(
        _('Plain Text'),
        help_text=_('The context available to you includes {{ ticket }}, '
            '{{ queue }}, and depending on the time of the call: '
            '{{ resolution }} or {{ comment }}.'),
        )

    html = models.TextField(
        _('HTML'),
        help_text=_('The same context is available here as in plain_text, '
            'above.'),
        )

    locale = models.CharField(
        _('Locale'),
        max_length=10,
        blank=True,
        null=True,
        help_text=_('Locale of this template.'),
        )

    def __str__(self):
        return '%s' % self.template_name

    class Meta:
        ordering = ['template_name', 'locale']
        verbose_name = _('e-mail template')
        verbose_name_plural = _('e-mail templates')


@python_2_unicode_compatible
class KBCategory(models.Model):
    """
    Lets help users help themselves: the Knowledge Base is a categorised
    listing of questions & answers.
    """

    title = models.CharField(
        _('Title'),
        max_length=100,
        )

    slug = models.SlugField(
        _('Slug'),
        )

    description = models.TextField(
        _('Description'),
        )

    def __str__(self):
        return '%s' % self.title

    class Meta:
        ordering = ['title',]
        verbose_name = _('Knowledge base category')
        verbose_name_plural = _('Knowledge base categories')

    def get_absolute_url(self):
        return ('helpdesk_kb_category', (), {'slug': self.slug})
    get_absolute_url = models.permalink(get_absolute_url)


@python_2_unicode_compatible
class KBItem(models.Model):
    """
    An item within the knowledgebase. Very straightforward question/answer
    style system.
    """
    category = models.ForeignKey(
        KBCategory,
        verbose_name=_('Category'),
        )

    title = models.CharField(
        _('Title'),
        max_length=100,
        )

    question = models.TextField(
        _('Question'),
        )

    answer = models.TextField(
        _('Answer'),
        )

    votes = models.IntegerField(
        _('Votes'),
        help_text=_('Total number of votes cast for this item'),
        default=0,
        )

    recommendations = models.IntegerField(
        _('Positive Votes'),
        help_text=_('Number of votes for this item which were POSITIVE.'),
        default=0,
        )

    last_updated = models.DateTimeField(
        _('Last Updated'),
        help_text=_('The date on which this question was most recently '
            'changed.'),
        blank=True,
        )

    def save(self, *args, **kwargs):
        if not self.last_updated:
            self.last_updated = timezone.now()
        return super(KBItem, self).save(*args, **kwargs)

    def _score(self):
        if self.votes > 0:
            return int(self.recommendations / self.votes)
        else:
            return _('Unrated')
    score = property(_score)

    def __str__(self):
        return '%s' % self.title

    class Meta:
        ordering = ['title',]
        verbose_name = _('Knowledge base item')
        verbose_name_plural = _('Knowledge base items')

    def get_absolute_url(self):
        return ('helpdesk_kb_item', (self.id,))
    get_absolute_url = models.permalink(get_absolute_url)


@python_2_unicode_compatible
class SavedSearch(models.Model):
    """
    Allow a user to save a ticket search, eg their filtering and sorting
    options, and optionally share it with other users. This lets people
    easily create a set of commonly-used filters, such as:
        * My tickets waiting on me
        * My tickets waiting on submitter
        * My tickets in 'Priority Support' queue with priority of 1
        * All tickets containing the word 'billing'.
         etc...
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_('User'),
        )

    title = models.CharField(
        _('Query Name'),
        max_length=100,
        help_text=_('User-provided name for this query'),
        )

    shared = models.BooleanField(
        _('Shared With Other Users?'),
        blank=True,
        default=False,
        help_text=_('Should other users see this query?'),
        )

    query = models.TextField(
        _('Search Query'),
        help_text=_('Pickled query object. Be wary changing this.'),
        )

    def __str__(self):
        if self.shared:
            return '%s (*)' % self.title
        else:
            return '%s' % self.title

    class Meta:
        verbose_name = _('Saved search')
        verbose_name_plural = _('Saved searches')


@python_2_unicode_compatible
class UserSettings(models.Model):
    """
    A bunch of user-specific settings that we want to be able to define, such
    as notification preferences and other things that should probably be
    configurable.

    We should always refer to user.usersettings.settings['setting_name'].
    """

    user = models.OneToOneField(settings.AUTH_USER_MODEL)

    settings_pickled = models.TextField(
        _('Settings Dictionary'),
        help_text=_('This is a base64-encoded representation of a pickled Python dictionary. Do not change this field via the admin.'),
        blank=True,
        null=True,
        )

    def _set_settings(self, data):
        # data should always be a Python dictionary.
        try:
            import pickle
        except ImportError:
            import cPickle as pickle
        from helpdesk.lib import b64encode
        self.settings_pickled = b64encode(pickle.dumps(data))

    def _get_settings(self):
        # return a python dictionary representing the pickled data.
        try:
            import pickle
        except ImportError:
            import cPickle as pickle
        from helpdesk.lib import b64decode
        try:
            return pickle.loads(b64decode(str(self.settings_pickled)))
        except pickle.UnpicklingError:
            return {}

    settings = property(_get_settings, _set_settings)

    def __str__(self):
        return 'Preferences for %s' % self.user

    class Meta:
        verbose_name = _('User Setting')
        verbose_name_plural = _('User Settings')


def create_usersettings(sender, instance, created, **kwargs):
    """
    Helper function to create UserSettings instances as
    required, eg when we first create the UserSettings database
    table via 'syncdb' or when we save a new user.

    If we end up with users with no UserSettings, then we get horrible
    'DoesNotExist: UserSettings matching query does not exist.' errors.
    """
    from helpdesk.settings import DEFAULT_USER_SETTINGS
    if created:
        UserSettings.objects.create(user=instance, settings=DEFAULT_USER_SETTINGS)

try:
    # Connecting via settings.AUTH_USER_MODEL (string) fails in Django < 1.7. We need the actual model there.
    # https://docs.djangoproject.com/en/1.7/topics/auth/customizing/#referencing-the-user-model
    if VERSION < (1, 7):
        raise ValueError
    models.signals.post_save.connect(create_usersettings, sender=settings.AUTH_USER_MODEL)
except:
    signal_user = get_user_model()
    models.signals.post_save.connect(create_usersettings, sender=signal_user)


@python_2_unicode_compatible
class IgnoreEmail(models.Model):
    """
    This model lets us easily ignore e-mails from certain senders when
    processing IMAP and POP3 mailboxes, eg mails from postmaster or from
    known trouble-makers.
    """
    queues = models.ManyToManyField(
        Queue,
        blank=True,
        help_text=_('Leave blank for this e-mail to be ignored on all '
            'queues, or select those queues you wish to ignore this e-mail '
            'for.'),
        )

    name = models.CharField(
        _('Name'),
        max_length=100,
        )

    date = models.DateField(
        _('Date'),
        help_text=_('Date on which this e-mail address was added'),
        blank=True,
        editable=False
        )

    email_address = models.CharField(
        _('E-Mail Address'),
        max_length=150,
        help_text=_('Enter a full e-mail address, or portions with '
            'wildcards, eg *@domain.com or postmaster@*.'),
        )

    keep_in_mailbox = models.BooleanField(
        _('Save Emails in Mailbox?'),
        blank=True,
        default=False,
        help_text=_('Do you want to save emails from this address in the '
            'mailbox? If this is unticked, emails from this address will '
            'be deleted.'),
        )

    def __str__(self):
        return '%s' % self.name

    def save(self, *args, **kwargs):
        if not self.date:
            self.date = timezone.now()
        return super(IgnoreEmail, self).save(*args, **kwargs)

    def test(self, email):
        """
        Possible situations:
            1. Username & Domain both match
            2. Username is wildcard, domain matches
            3. Username matches, domain is wildcard
            4. username & domain are both wildcards
            5. Other (no match)

            1-4 return True, 5 returns False.
        """

        own_parts = self.email_address.split("@")
        email_parts = email.split("@")

        if self.email_address == email                              \
        or own_parts[0] == "*" and own_parts[1] == email_parts[1]   \
        or own_parts[1] == "*" and own_parts[0] == email_parts[0]   \
        or own_parts[0] == "*" and own_parts[1] == "*":
            return True
        else:
            return False

    class Meta:
        verbose_name = _('Ignored e-mail address')
        verbose_name_plural = _('Ignored e-mail addresses')


@python_2_unicode_compatible
class TicketCC(models.Model):
    """
    Often, there are people who wish to follow a ticket who aren't the
    person who originally submitted it. This model provides a way for those
    people to follow a ticket.

    In this circumstance, a 'person' could be either an e-mail address or
    an existing system user.
    """

    ticket = models.ForeignKey(
        Ticket,
        verbose_name=_('Ticket'),
        )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        help_text=_('User who wishes to receive updates for this ticket.'),
        verbose_name=_('User'),
        )

    email = models.EmailField(
        _('E-Mail Address'),
        blank=True,
        null=True,
        help_text=_('For non-user followers, enter their e-mail address'),
        )

    can_view = models.BooleanField(
        _('Can View Ticket?'),
        blank=True,
        default=False,
        help_text=_('Can this CC login to view the ticket details?'),
        )

    can_update = models.BooleanField(
        _('Can Update Ticket?'),
        blank=True,
        default=False,
        help_text=_('Can this CC login and update the ticket?'),
        )

    def _email_address(self):
        if self.user and self.user.email is not None:
            return self.user.email
        else:
            return self.email
    email_address = property(_email_address)

    def _display(self):
        if self.user:
            return self.user
        else:
            return self.email
    display = property(_display)

    def __str__(self):
        return '%s for %s' % (self.display, self.ticket.title)

class CustomFieldManager(models.Manager):
    def get_queryset(self):
        return super(CustomFieldManager, self).get_queryset().order_by('ordering')


@python_2_unicode_compatible
class CustomField(models.Model):
    """
    Definitions for custom fields that are glued onto each ticket.
    """

    name = models.SlugField(
        _('Field Name'),
        help_text=_('As used in the database and behind the scenes. Must be unique and consist of only lowercase letters with no punctuation.'),
        unique=True,
        )

    label = models.CharField(
        _('Label'),
        max_length=30,
        help_text=_('The display label for this field'),
        )

    help_text = models.TextField(
        _('Help Text'),
        help_text=_('Shown to the user when editing the ticket'),
        blank=True,
        null=True
        )

    DATA_TYPE_CHOICES = (
            ('varchar', _('Character (single line)')),
            ('text', _('Text (multi-line)')),
            ('integer', _('Integer')),
            ('decimal', _('Decimal')),
            ('list', _('List')),
            ('boolean', _('Boolean (checkbox yes/no)')),
            ('date', _('Date')),
            ('time', _('Time')),
            ('datetime', _('Date & Time')),
            ('email', _('E-Mail Address')),
            ('url', _('URL')),
            ('ipaddress', _('IP Address')),
            ('slug', _('Slug')),
            )

    data_type = models.CharField(
        _('Data Type'),
        max_length=100,
        help_text=_('Allows you to restrict the data entered into this field'),
        choices=DATA_TYPE_CHOICES,
        )

    max_length = models.IntegerField(
        _('Maximum Length (characters)'),
        blank=True,
        null=True,
        )

    decimal_places = models.IntegerField(
        _('Decimal Places'),
        help_text=_('Only used for decimal fields'),
        blank=True,
        null=True,
        )

    empty_selection_list = models.BooleanField(
        _('Add empty first choice to List?'),
        default=False,
        help_text=_('Only for List: adds an empty first entry to the choices list, which enforces that the user makes an active choice.'),
        )

    list_values = models.TextField(
        _('List Values'),
        help_text=_('For list fields only. Enter one option per line.'),
        blank=True,
        null=True,
        )

    ordering = models.IntegerField(
        _('Ordering'),
        help_text=_('Lower numbers are displayed first; higher numbers are listed later'),
        blank=True,
        null=True,
        )

    def _choices_as_array(self):
        from StringIO import StringIO
        valuebuffer = StringIO(self.list_values)
        choices = [[item.strip(), item.strip()] for item in valuebuffer.readlines()]
        valuebuffer.close()
        return choices
    choices_as_array = property(_choices_as_array)

    required = models.BooleanField(
        _('Required?'),
        help_text=_('Does the user have to enter a value for this field?'),
        default=False,
        )

    staff_only = models.BooleanField(
        _('Staff Only?'),
        help_text=_('If this is ticked, then the public submission form will NOT show this field'),
        default=False,
        )

    objects = CustomFieldManager()

    def __str__(self):
        return '%s' % (self.name)

    class Meta:
        verbose_name = _('Custom field')
        verbose_name_plural = _('Custom fields')


@python_2_unicode_compatible
class TicketCustomFieldValue(models.Model):
    ticket = models.ForeignKey(
        Ticket,
        verbose_name=_('Ticket'),
        )

    field = models.ForeignKey(
        CustomField,
        verbose_name=_('Field'),
        )

    value = models.TextField(blank=True, null=True)

    def __str__(self):
        return '%s / %s' % (self.ticket, self.field)

    class Meta:
        unique_together = ('ticket', 'field'),

    class Meta:
        verbose_name = _('Ticket custom field value')
        verbose_name_plural = _('Ticket custom field values')


@python_2_unicode_compatible
class TicketDependency(models.Model):
    """
    The ticket identified by `ticket` cannot be resolved until the ticket in `depends_on` has been resolved.
    To help enforce this, a helper function `can_be_resolved` on each Ticket instance checks that
    these have all been resolved.
    """
    ticket = models.ForeignKey(
        Ticket,
        verbose_name=_('Ticket'),
        related_name='ticketdependency',
        )

    depends_on = models.ForeignKey(
        Ticket,
        verbose_name=_('Depends On Ticket'),
        related_name='depends_on',
        )

    def __str__(self):
        return '%s / %s' % (self.ticket, self.depends_on)

    class Meta:
        unique_together = ('ticket', 'depends_on')
        verbose_name = _('Ticket dependency')
        verbose_name_plural = _('Ticket dependencies')


class SLADefinition(models.Model):
    PRIORITY_CHOICES = (
        (1, _('1. Critical')),
        (2, _('2. High')),
        (3, _('3. Normal')),
        (4, _('4. Low')),
        (5, _('5. Very Low')),
    )

    LEVEL_CHOICES = (
        (1, _('1. Level 1 escalation')),
        (2, _('2. Level 2 escalation')),
        (3, _('3. Level 3 escalation')),
    )

    queue = models.ForeignKey(Queue, related_name='slaqueue', related_query_name='slaqueue')
    priority = models.IntegerField(choices=PRIORITY_CHOICES)
    level = models.IntegerField(choices=LEVEL_CHOICES)
    SLA = models.IntegerField(help_text="In minutes")
    escalate_to_email = models.EmailField(blank=True, null=True, help_text="Email id for this type of escalation")
    escalate_to_phone = models.CharField(blank=True, null=True, max_length=15, help_text="Mobile number for this type of escalation")

    def __unicode__(self):
        return "_".join([str(self.queue.title) , str(self.priority) , str(self.level) , str(self.escalate_to_email)])

    class Meta:
        unique_together = ('queue', 'priority', 'level', 'escalate_to_email')


def my_custom_sql(query, params):
    logger.debug(query)
    logger.debug(params)
    with connection.cursor() as cursor:
        try:
            cursor.execute(query, params)
            return cursor.fetchall()
        except Exception as exc:
            logger.debug(str(exc))
            return None


class TicketsReports(object):

    @staticmethod
    def _tickets_events_summary_all(plants, st, et, grouping):
        try:
            assert (grouping == "YEARLY" or grouping == "MONTHLY" or grouping == "DAILY")
        except :
            raise ValidationError("This grouping is not possible")

        query = None
        queues_ids = []
        for plant in plants:
            try:
                queues_ids.append(plant.queues.all()[0].id)
            except:
                continue

        if grouping == "YEARLY":
            query = "SELECT COUNT(*), event_type, year(created), avg(expected_energy - actual_energy) as avg_loss " \
                    "from helpdesk_ticket WHERE queue_id IN %s AND created >= %s AND created <= %s GROUP BY " \
                    "event_type, year(created)"

        elif grouping == "MONTHLY":
            query = "SELECT COUNT(*), event_type, year(created), month(created), avg(expected_energy - actual_energy) " \
                    "as avg_loss from helpdesk_ticket WHERE queue_id IN %s AND created >= %s AND created <= %s GROUP BY " \
                    "event_type, year(created), month(created)"

        elif grouping == "DAILY":
            query = "SELECT COUNT(*), event_type, year(created), month(created), date(created), " \
                    "avg(expected_energy - actual_energy) as avg_loss " \
                    "from helpdesk_ticket WHERE queue_id IN %s AND created >= %s AND created <= %s GROUP BY " \
                    "event_type, year(created), month(created), date(created)"

        try:
            if query:
                results = my_custom_sql(query, [tuple(queues_ids), st, et])
                return results
            else:
                raise ValidationError("Unknown error")
        except Exception as exc:
            logger.debug(exc)
            return None


    @staticmethod
    def _tickets_associations_events_summary_all(identifiers, st, et, grouping):
        try:
            assert (grouping == "YEARLY" or grouping == "MONTHLY" or grouping == "DAILY")
        except :
            raise ValidationError("This grouping is not possible")

        query = None
        if grouping == "YEARLY":
            query = "SELECT COUNT(*), event_type, year(created), avg(actual_energy - expected_energy) as mttr,AVG(ROUND(time_to_sec((TIMEDIFF(closed, created))) / 60)) from helpdesk_ticketassociation WHERE identifier IN %s AND created >= %s AND created <= %s GROUP BY event_type, year(created)"

        elif grouping == "MONTHLY":
            query = "SELECT COUNT(*), event_type, year(created), month(created), avg(actual_energy - expected_energy) as mttr, AVG(dateiff(minute, created, closed)) " \
                    "from helpdesk_ticketassociation WHERE identifier IN %s AND created >= %s AND created <= %s GROUP " \
                    "BY event_type, year(created), month(created)"

        elif grouping == "DAILY":
            query = "SELECT COUNT(*), event_type, year(created), month(created), date(created), avg(actual_energy - expected_energy) as mttr, AVG(dateiff(minute, created, closed)) " \
                    "from helpdesk_ticketassociation WHERE identifier IN %s AND created >= %s AND created <= %s GROUP " \
                    "BY event_type, year(created), month(created), date(created)"

        try:
            if query:
                results = my_custom_sql(query, [tuple(identifiers), st, et])
                return results
            else:
                raise ValidationError("Unknown error")

        except:
            return None

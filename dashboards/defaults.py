from django.core.urlresolvers import reverse_lazy
from django.shortcuts import redirect, render
from django.http import Http404
from organizations.backends.tokens import RegistrationTokenGenerator
from django.conf.urls import patterns, url
from django.utils.translation import ugettext as _

from allauth.account.models import EmailAddress


from organizations.backends.forms import UserRegistrationForm
from organizations.backends.defaults import InvitationBackend
import logging

logger = logging.getLogger('dataglen.views')
logger.setLevel(logging.DEBUG)


class DataglenInvitationBackend(InvitationBackend):
    def get_success_url(self):
        return reverse_lazy('account_login')

    def activate_view(self, request, user_id, token):
        try:
            user = self.user_model.objects.get(id=user_id, is_active=False)
        except self.user_model.DoesNotExist:
            raise Http404(_("Your URL may have expired."))

        if not RegistrationTokenGenerator().check_token(user, token):
            raise Http404(_("Your URL may have expired."))
        form = self.get_form(data=request.POST or None, instance=user)
        if form.is_valid():
            form.instance.is_active = True
            user = form.save()
            user.set_password(form.cleaned_data['password'])
            user.save()
            ed = EmailAddress(user=user, email=user.email, primary=True, verified=True)
            ed.save()
            #self.activate_organizations(user)
            return redirect(self.get_success_url())

        return render(request, 'organizations/register_form.html', {'form': form})
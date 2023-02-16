from django import forms
from django_comments.forms import CommentForm
from dgcomments.models import DgComment


class DgCommentForm(CommentForm):
    title = forms.CharField(max_length=300)

    def get_comment_model(self):
        # Use our custom comment model instead of the built-in one.
        return DgComment

    def get_comment_create_data(self):
        # Use the data of the superclass, and add in the image base 64 field
        data = super(DgComment, self).get_comment_create_data()
        data['image_base_64'] = self.cleaned_data['image_base_64']
        return data
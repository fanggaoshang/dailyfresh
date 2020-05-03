from django.contrib.auth.decorators import login_required


class LoginRequiresMixin(object):
    @classmethod
    def as_view(cls, **initkwargs):
        view = super(LoginRequiresMixin, cls).as_view(**initkwargs)
        return login_required(view)


# -*- coding: utf-8 -*-
from cms.utils.compat import DJANGO_1_10
from django.contrib.admin.templatetags.admin_static import static
from django.contrib.auth import get_permission_codename
from django.contrib.sites.models import Site
from django.core.urlresolvers import NoReverseMatch, reverse_lazy
from django.forms.widgets import Select, MultiWidget, TextInput
from django.utils.encoding import force_text
from django.utils.html import escape, escapejs
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _

from cms.utils.urlutils import admin_reverse, static_with_version
from cms.forms.utils import get_site_choices, get_page_choices
from cms.models import Page, PageUser


class PageSelectWidget(MultiWidget):
    """A widget that allows selecting a page by first selecting a site and then
    a page on that site in a two step process.
    """
    template_name = 'cms/widgets/pageselectwidget.html'

    class Media:
        js = (
            static_with_version('cms/js/dist/bundle.forms.pageselectwidget.min.js'),
        )

    def __init__(self, site_choices=None, page_choices=None, attrs=None):
        if attrs is not None:
            self.attrs = attrs.copy()
        else:
            self.attrs = {}
        self.choices = []
        super(PageSelectWidget, self).__init__((Select, Select, Select), attrs)

    def decompress(self, value):
        """
        receives a page_id in value and returns the site_id and page_id
        of that page or the current site_id and None if no page_id is given.
        """
        if value:
            page = Page.objects.get(pk=value)
            site = page.site
            return [site.pk, page.pk, page.pk]
        site = Site.objects.get_current()
        return [site.pk,None,None]

    def _has_changed(self, initial, data):
        # THIS IS A COPY OF django.forms.widgets.Widget._has_changed()
        # (except for the first if statement)

        """
        Return True if data differs from initial.
        """
        # For purposes of seeing whether something has changed, None is
        # the same as an empty string, if the data or inital value we get
        # is None, replace it w/ u''.
        if data is None or (len(data)>=2 and data[1] in [None,'']):
            data_value = u''
        else:
            data_value = data
        if initial is None:
            initial_value = u''
        else:
            initial_value = initial
        if force_text(initial_value) != force_text(data_value):
            return True
        return False

    def _build_widgets(self):
        site_choices = get_site_choices()
        page_choices = get_page_choices()
        self.site_choices = site_choices
        self.choices = page_choices
        self.widgets = (Select(choices=site_choices ),
                   Select(choices=[('', '----')]),
                   Select(choices=self.choices, attrs={'style': "display:none;"} ),
        )

    def _build_script(self, name, value, attrs={}):
        return r"""<script type="text/javascript">
                var CMS = window.CMS || {};

                CMS.Widgets = CMS.Widgets || {};
                CMS.Widgets._pageSelectWidgets = CMS.Widgets._pageSelectWidgets || [];
                CMS.Widgets._pageSelectWidgets.push({
                    name: '%(name)s'
                });
            </script>""" % {
                'name': name
            }

    def get_context(self, name, value, attrs):
        self._build_widgets()
        context = super(PageSelectWidget, self).get_context(name, value, attrs)
        context['widget']['script_init'] = self._build_script(name, value, context['widget']['attrs'])
        return context

    def render(self, name, value, attrs=None, renderer=None):
        if DJANGO_1_10:
            # THIS IS A COPY OF django.forms.widgets.MultiWidget.render()
            # (except for the last line)

            # value is a list of values, each corresponding to a widget
            # in self.widgets.
            self._build_widgets()

            if not isinstance(value, list):
                value = self.decompress(value)
            output = []
            final_attrs = self.build_attrs(attrs)
            id_ = final_attrs.get('id', None)
            for i, widget in enumerate(self.widgets):
                try:
                    widget_value = value[i]
                except IndexError:
                    widget_value = None
                if id_:
                    final_attrs = dict(final_attrs, id='%s_%s' % (id_, i))
                output.append(widget.render(name + '_%s' % i, widget_value, final_attrs))
            output.append(self._build_script(name, value, final_attrs))
            return mark_safe(self.format_output(output))
        else:
            return super(PageSelectWidget, self).render(name, value, attrs, renderer)

    def format_output(self, rendered_widgets):
        return u' '.join(rendered_widgets)


class PageSmartLinkWidget(TextInput):
    template_name = 'cms/widgets/pagesmartlinkwidget.html'

    class Media:
        css = {
            'all': (
                'cms/js/select2/select2.css',
                'cms/js/select2/select2-bootstrap.css',
            )
        }
        js = (
            static_with_version('cms/js/dist/bundle.forms.pagesmartlinkwidget.min.js'),
        )

    def __init__(self, attrs=None, ajax_view=None):
        super(PageSmartLinkWidget, self).__init__(attrs)
        self.ajax_url = self.get_ajax_url(ajax_view=ajax_view)

    def get_ajax_url(self, ajax_view):
        try:
            return reverse_lazy(ajax_view)
        except NoReverseMatch:
            raise Exception(
                'You should provide an ajax_view argument that can be reversed to the PageSmartLinkWidget'
            )

    def _build_script(self, name, value, attrs={}):
        return r"""<script type="text/javascript">
            var CMS = window.CMS || {};

            CMS.Widgets = CMS.Widgets || {};
            CMS.Widgets._pageSmartLinkWidgets = CMS.Widgets._pageSmartLinkWidgets || [];
            CMS.Widgets._pageSmartLinkWidgets.push({
                id: '%(element_id)s',
                text: '%(placeholder_text)s',
                lang: '%(language_code)s',
                url: '%(ajax_url)s'
            });
        </script>""" % {
            'element_id': attrs.get('id', ''),
            'placeholder_text': attrs.get('placeholder_text', ''),
            'language_code': self.language,
            'ajax_url': force_text(self.ajax_url)
        }

    def get_context(self, name, value, attrs):
        context = super(PageSmartLinkWidget, self).get_context(name, value, attrs)
        context['widget']['script_init'] = self._build_script(name, value, context['widget']['attrs'])
        return context

    def render(self, name, value, attrs=None, renderer=None):
        if DJANGO_1_10:
            final_attrs = self.build_attrs(attrs)
            output = list(self._build_script(name, value, final_attrs))
            output.append(super(PageSmartLinkWidget, self).render(name, value, attrs))
            return mark_safe(u''.join(output))
        else:
            return super(PageSmartLinkWidget, self).render(name, value, attrs, renderer)


class UserSelectAdminWidget(Select):
    """Special widget used in page permission inlines, because we have to render
    an add user (plus) icon, but point it somewhere else - to special user creation
    view, which is accessible only if user haves "add user" permissions.

    Current user should be assigned to widget in form constructor as an user
    attribute.
    """
    def render(self, name, value, attrs=None, choices=()):
        output = [super(UserSelectAdminWidget, self).render(name, value, attrs)]
        if hasattr(self, 'user') and (self.user.is_superuser or \
            self.user.has_perm(PageUser._meta.app_label + '.' + get_permission_codename('add', PageUser._meta))):
            # append + icon
            add_url = admin_reverse('cms_pageuser_add')
            output.append(u'<a href="%s" class="add-another" id="add_id_%s" onclick="return showAddAnotherPopup(this);"> ' % \
                    (add_url, name))
        return mark_safe(u''.join(output))


class AppHookSelect(Select):

    """Special widget used for the App Hook selector in the Advanced Settings
    of the Page Admin. It adds support for a data attribute per option and
    includes supporting JS into the page.
    """

    class Media:
        js = (
            static_with_version('cms/js/dist/bundle.forms.apphookselect.min.js'),
        )

    def __init__(self, attrs=None, choices=(), app_namespaces={}):
        self.app_namespaces = app_namespaces
        super(AppHookSelect, self).__init__(attrs, choices)

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super(AppHookSelect, self).create_option(name, value, label, selected, index, subindex, attrs)
        if value in self.app_namespaces:
            option['attrs']['data-namespace'] = escape(self.app_namespaces[value])
        return option

    def _build_option(self, selected_choices, option_value, option_label):
        if option_value is None:
            option_value = ''
        option_value = force_text(option_value)
        if option_value in selected_choices:
            selected_html = mark_safe(' selected="selected"')
            if not self.allow_multiple_selected:
                # Only allow for a single selection.
                selected_choices.remove(option_value)
        else:
            selected_html = ''

        if option_value in self.app_namespaces:
            data_html = mark_safe(' data-namespace="%s"' % escape(self.app_namespaces[option_value]))
        else:
            data_html = ''
        return option_value, selected_html, data_html, force_text(option_label)

    def render_option(self, selected_choices, option_value, option_label):
        option_data = self._build_option(selected_choices, option_value, option_label)
        return '<option value="%s"%s%s>%s</option>' % option_data


class ApplicationConfigSelect(Select):
    """
    Special widget -populate by javascript- that shows application configurations
    depending on selected Apphooks.

    Required data are injected in the page as javascript data that cms.app_hook_select.js
    uses to create the appropriate data structure.

    A stub 'add-another' link is created and filled in with the correct URL by the same
    javascript.
    """
    template_name = 'cms/widgets/applicationconfigselect.html'

    class Media:
        js = (
            static_with_version('cms/js/dist/bundle.forms.apphookselect.min.js'),
        )

    def __init__(self, attrs=None, choices=(), app_configs={}):
        self.app_configs = app_configs
        super(ApplicationConfigSelect, self).__init__(attrs, choices)

    def _build_script(self, name, value, attrs={}):
        configs = []
        urls = []
        for application, cms_app in self.app_configs.items():
            configs.append("'%s': [%s]" % (application, ",".join(
                ["['%s', '%s']" % (config.pk, escapejs(escape(config))) for config in cms_app.get_configs()])))  # noqa
        for application, cms_app in self.app_configs.items():
            urls.append("'%s': '%s'" % (application, cms_app.get_config_add_url()))
        return r"""<script type="text/javascript">
            var apphooks_configuration = {
                %(apphooks_configurations)s
            };
            var apphooks_configuration_url = {
                %(apphooks_url)s
            };
            var apphooks_configuration_value = '%(apphooks_value)s';
        </script>""" % {
            'apphooks_configurations': ','.join(configs),
            'apphooks_url': ','.join(urls),
            'apphooks_value': value,
        }

    def get_context(self, name, value, attrs):
        context = super(ApplicationConfigSelect, self).get_context(name, value, attrs)
        context['widget']['script_init'] = self._build_script(name, value, context['widget']['attrs'])
        return context

    def render(self, name, value, attrs=None, renderer=None):
        if DJANGO_1_10:
            output = list(super(ApplicationConfigSelect, self).render(name, value, attrs))
            output.append(self._build_script(name, value, attrs))

            related_url = ''
            output.append('<a href="%s" class="add-another" id="add_%s" onclick="return showAddAnotherPopup(this);"> '
                          % (related_url, name))
            output.append('<img src="%s" width="10" height="10" alt="%s"/></a>'
                          % (static('admin/img/icon_addlink.gif'), _('Add Another')))
            return mark_safe(''.join(output))
        else:
            return super(ApplicationConfigSelect, self).render(name, value, attrs, renderer)

#!/usr/bin/env python
# crate_anon/crateweb/extra/admin.py

"""
===============================================================================
    Copyright (C) 2015-2017 Rudolf Cardinal (rudolf@pobox.com).

    This file is part of CRATE.

    CRATE is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    CRATE is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with CRATE. If not, see <http://www.gnu.org/licenses/>.
===============================================================================
"""

import logging
from typing import Any, Callable, Dict, List, Type

from django.contrib.admin import AdminSite, ModelAdmin
from django.contrib.admin.views.main import ChangeList
from django.core.urlresolvers import reverse
from django.db.models import Model
from django.forms import ModelForm
from django.http import HttpResponse
from django.http.request import HttpRequest
from django.utils.encoding import force_text
from django.utils.html import escape
from django.utils.translation import ugettext

log = logging.getLogger(__name__)


# =============================================================================
# Action-restricted ModelAdmin classes
# =============================================================================

class ReadOnlyChangeList(ChangeList):
    # See ChangeList in django.contrib.admin.views.main
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        if self.is_popup:
            title = ugettext('Select %s')
        else:
            title = ugettext('Select %s to view')
        self.title = title % force_text(self.opts.verbose_name)


class ReadOnlyModelAdmin(ModelAdmin):
    """
    Allows view ("change"), but not add/edit/delete.

    You also need to do this:
        my_admin_site.index_template = 'admin/viewchange_admin_index.html'
    ... to give a modified admin/index.html that says "View/change" not
    "Change".

    """
    # http://stackoverflow.com/questions/3068843/permission-to-view-but-not-to-change-django  # noqa
    # See also http://stackoverflow.com/questions/6680631/django-admin-separate-read-only-view-and-change-view  # noqa
    # django/contrib/admin/templates/admin/change_form.html
    # django/contrib/admin/templatetags/admin_modify.py
    # https://docs.djangoproject.com/en/1.8/ref/contrib/admin/#django.contrib.ModelAdmin.change_view  # noqa

    # Remove the tickbox for deletion, and the top/bottom action bars:
    actions = None

    # When you drill down into a single object, use a custom template
    # that removes the 'save' buttons:
    change_form_template = 'admin/readonly_view_form.html'

    def has_add_permission(self, request: HttpRequest, obj=None) -> bool:
        # Don't let the user add objects.
        return False

    def has_delete_permission(self, request: HttpRequest, obj=None) -> bool:
        # Don't let the user delete objects.
        return False

    # Don't remove has_change_permission, or you won't see anything.
    # def has_change_permission(self, request, obj=None):
    #     return False

    def save_model(self, request: HttpRequest, obj, 
                   form: ModelForm, change: bool):
        # Return nothing to make sure user can't update any data
        pass

    # Make list say "Select [model] to view" not "... change"
    def get_changelist(self, request: HttpRequest, **kwargs) \
            -> Type[ChangeList]:
        return ReadOnlyChangeList

    # Make single object view say "View [model]", not "Change [model]"
    def change_view(self, 
                    request: HttpRequest, 
                    object_id: int, 
                    form_url: str = '', 
                    extra_context: Dict[str, Any] = None) -> HttpResponse:
        extra_context = extra_context or {}
        # noinspection PyProtectedMember
        extra_context["title"] = "View %s" % force_text(
            self.model._meta.verbose_name)
        return super().change_view(request, object_id, form_url,
                                   extra_context=extra_context)


class AddOnlyModelAdmin(ModelAdmin):
    """
    Allows add, but not edit or delete.
    Optional extra class attribute:
        fields_for_viewing
    """
    actions = None

    # When you drill down into a single object, use a custom template
    # that removes the 'save' buttons:
    change_form_template = 'admin/readonly_view_form.html'

    # But keep the default for adding:
    add_form_template = 'admin/change_form.html'

    def has_delete_permission(self, request: HttpRequest, obj=None) -> bool:
        return False

    def get_changelist(self, request: HttpRequest, **kwargs) \
            -> Type[ChangeList]:
        return ReadOnlyChangeList

    # This is an add-but-not-edit class.
    # http://stackoverflow.com/questions/7860612/django-admin-make-field-editable-in-add-but-not-edit  # noqa
    def get_readonly_fields(self, request: HttpRequest, obj=None) -> List[str]:
        if obj:  # obj is not None, so this is an edit
            # self.__class__ is the derived class
            if hasattr(self.__class__, 'fields_for_viewing'):
                return self.__class__.fields_for_viewing
            elif hasattr(self.__class__, 'readonly_fields'):
                return self.__class__.readonly_fields
            else:
                return self.__class__.fields
        else:  # This is an addition
            return []

    def get_fields(self, request: HttpRequest, obj=None) -> List[str]:
        if obj:  # edit (view)
            return self.__class__.fields_for_viewing
        else:
            return self.__class__.fields

    # Make single object view say "View [model]", not "Change [model]"
    def change_view(self, 
                    request: HttpRequest, 
                    object_id: int, 
                    form_url: str = '', 
                    extra_context: Dict[str, Any] = None) -> HttpResponse:
        extra_context = extra_context or {}
        # noinspection PyProtectedMember
        extra_context["title"] = "View %s" % force_text(
            self.model._meta.verbose_name)
        return super().change_view(request, object_id, form_url,
                                   extra_context=extra_context)


class EditOnlyModelAdmin(ModelAdmin):
    """
    Allows editing, but not add or delete.
    Designed for e.g. when you have a fixed set of PKs.
    In that situation, ensure the PK field is in readonly_fields.
    """
    actions = None

    def has_add_permission(self, request: HttpRequest, obj=None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj=None) -> bool:
        return False


class EditOnceOnlyModelAdmin(ModelAdmin):
    """
    Allows editing, but not add or delete.
    Designed for e.g. when you have a fixed set of PKs.
    In that situation, ensure the PK field is in readonly_fields.
    """
    actions = None

    change_form_template = 'admin/edit_once_view_form.html'

    def has_add_permission(self, request: HttpRequest, obj=None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj=None) -> bool:
        return False


class AllStaffReadOnlyModelAdmin(ReadOnlyModelAdmin):
    """
    ReadOnlyModelAdmin but allows access to all staff, not just superusers.
    (No easy way to make this work via multiple inheritance.)
    """
    def has_module_permission(self, request: HttpRequest) -> bool:
        return request.user.is_staff

    def has_change_permission(self, request: HttpRequest, obj=None) -> bool:
        return request.user.is_staff


# =============================================================================
# Links in model admin
# =============================================================================

# noinspection PyProtectedMember
def admin_view_url(admin_site: AdminSite, 
                   obj, 
                   view_type: str = "change", 
                   current_app: str = None) -> str:
    app_name = obj._meta.app_label.lower()
    model_name = obj._meta.object_name.lower()
    pk = obj.pk
    viewname = "admin:{}_{}_{}".format(app_name, model_name, view_type)
    if current_app is None:
        current_app = admin_site.name
    url = reverse(viewname, args=[pk], current_app=current_app)
    return url


# noinspection PyProtectedMember
def admin_view_fk_link(modeladmin: ModelAdmin,
                       obj,
                       fkfield: str,
                       missing: str = "(None)",
                       use_str: bool = True,
                       view_type: str = "change",
                       current_app: str = None) -> str:
    if not hasattr(obj, fkfield):
        return missing
    linked_obj = getattr(obj, fkfield)
    app_name = linked_obj._meta.app_label.lower()
    model_name = linked_obj._meta.object_name.lower()
    viewname = "admin:{}_{}_{}".format(app_name, model_name, view_type)
    # https://docs.djangoproject.com/en/dev/ref/contrib/admin/#reversing-admin-urls  # noqa
    if current_app is None:
        current_app = modeladmin.admin_site.name
        # ... plus a bit of home-grown magic; see Django source
    url = reverse(viewname, args=[linked_obj.pk], current_app=current_app)
    if use_str:
        label = escape(str(linked_obj))
    else:
        label = "{} {}".format(escape(linked_obj._meta.object_name),
                               linked_obj.pk)
    return '<a href="{}">{}</a>'.format(url, label)


# noinspection PyProtectedMember
def admin_view_reverse_fk_links(modeladmin: ModelAdmin,
                                obj,
                                reverse_fk_set_field: str,
                                missing: str = "(None)",
                                use_str: bool = True,
                                separator: str = "<br>",
                                view_type: str = "change",
                                current_app: str = None) -> str:
    if not hasattr(obj, reverse_fk_set_field):
        return missing
    linked_objs = getattr(obj, reverse_fk_set_field).all()
    if not linked_objs:
        return missing
    first = linked_objs[0]
    app_name = first._meta.app_label.lower()
    model_name = first._meta.object_name.lower()
    viewname = "admin:{}_{}_{}".format(app_name, model_name, view_type)
    if current_app is None:
        current_app = modeladmin.admin_site.name
    links = []
    for linked_obj in linked_objs:
        # log.debug("linked_obj: {}".format(linked_obj))
        url = reverse(viewname, args=[linked_obj.pk], current_app=current_app)

        if use_str:
            label = escape(str(linked_obj))
        else:
            label = "{} {}".format(escape(linked_obj._meta.object_name),
                                   linked_obj.pk)
        links.append('<a href="{}">{}</a>'.format(url, label))
    # log.debug("links: {}".format(links))
    return separator.join(links)


# =============================================================================
# Disable boolean icons for a ModelAdmin field
# =============================================================================
# http://stackoverflow.com/questions/13990846/disable-on-off-icon-for-boolean-field-in-django  # noqa
# ... extended to use closures

def disable_bool_icon(fieldname: str, model: Model) -> Callable[[Any], bool]:
    # noinspection PyUnusedLocal
    def func(self, obj):
        return getattr(obj, fieldname)
    func.boolean = False
    func.admin_order_field = fieldname
    # func.short_description = \
    #     model._meta.get_field_by_name(fieldname)[0].verbose_name
    # get_field_by_name() deprecated in Django 1.9 and will go in 1.10
    # https://docs.djangoproject.com/en/1.8/ref/models/meta/
    # noinspection PyProtectedMember
    func.short_description = \
        model._meta.get_field(fieldname).verbose_name
    return func

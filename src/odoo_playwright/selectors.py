"""Version-specific selectors for Odoo 16, 17, 18, 19."""

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class OdooSelectors:
    version: int

    MENU_ITEM = "menu_item"
    SUBMENU_ITEM = "submenu_item"
    VIEW_SWITCHER = "view_switcher"
    BUTTON_CREATE = "button_create"
    BUTTON_SAVE = "button_save"
    BUTTON_EDIT = "button_edit"
    BUTTON_DISCARD = "button_discard"
    BUTTON_DELETE = "button_delete"
    BUTTON_ACTION = "button_action"
    SEARCH_INPUT = "search_input"
    SEARCH_CLEAR = "search_clear"
    PAGER_NEXT = "pager_next"
    PAGER_PREV = "pager_prev"
    PAGER_INFO = "pager_info"
    LIST_ROW = "list_row"
    LIST_CELL = "list_cell"
    LIST_CHECKBOX = "list_checkbox"
    FORM_FIELD = "form_field"
    FORM_TAB = "form_tab"
    KANBAN_CARD = "kanban_card"
    KANBAN_COLUMN = "kanban_column"
    MODAL = "modal"
    NOTIFICATION = "notification"
    LOADING = "loading"
    BREADCRUMB = "breadcrumb"
    STATUSBAR = "statusbar"
    DROPDOWN = "dropdown"
    MANY2ONE = "many2one"
    BINARY_UPLOAD = "binary_upload"
    DATEPICKER = "datepicker"

    def get(self, key: str) -> str:
        selectors = SELECTORS_BY_VERSION.get(self.version, SELECTORS_V17)
        return selectors.get(key, "")


SELECTORS_V16: Dict[str, str] = {
    OdooSelectors.MENU_ITEM: ".o_menu_entry",
    OdooSelectors.SUBMENU_ITEM: ".o_menu_entry_lvl_2, .o_menu_entry_lvl_3",
    OdooSelectors.VIEW_SWITCHER: ".o_cp_switch_buttons button",
    OdooSelectors.BUTTON_CREATE: "button.o_form_button_create, button.o_list_button_add",
    OdooSelectors.BUTTON_SAVE: "button.o_form_button_save",
    OdooSelectors.BUTTON_EDIT: "button.o_form_button_edit",
    OdooSelectors.BUTTON_DISCARD: "button.o_form_button_cancel",
    OdooSelectors.BUTTON_DELETE: "button.o_form_button_delete",
    OdooSelectors.BUTTON_ACTION: ".o_cp_action_menus button",
    OdooSelectors.SEARCH_INPUT: ".o_searchview_input",
    OdooSelectors.SEARCH_CLEAR: ".o_searchview_facet_remove",
    OdooSelectors.PAGER_NEXT: ".o_pager_next",
    OdooSelectors.PAGER_PREV: ".o_pager_previous",
    OdooSelectors.PAGER_INFO: ".o_pager_counter",
    OdooSelectors.LIST_ROW: ".o_data_row",
    OdooSelectors.LIST_CELL: ".o_data_cell",
    OdooSelectors.LIST_CHECKBOX: ".o_list_record_selector input",
    OdooSelectors.FORM_FIELD: ".o_field_widget",
    OdooSelectors.FORM_TAB: ".o_notebook_tabs .nav-link",
    OdooSelectors.KANBAN_CARD: ".o_kanban_record",
    OdooSelectors.KANBAN_COLUMN: ".o_kanban_group",
    OdooSelectors.MODAL: ".modal-dialog",
    OdooSelectors.NOTIFICATION: ".o_notification",
    OdooSelectors.LOADING: ".o_loading",
    OdooSelectors.BREADCRUMB: ".o_breadcrumb",
    OdooSelectors.STATUSBAR: ".o_statusbar_buttons",
    OdooSelectors.DROPDOWN: ".o_dropdown_menu",
    OdooSelectors.MANY2ONE: ".o_field_many2one input",
    OdooSelectors.BINARY_UPLOAD: ".o_form_binary_file",
    OdooSelectors.DATEPICKER: ".o_datepicker_input",
}

SELECTORS_V17: Dict[str, str] = {
    OdooSelectors.MENU_ITEM: ".o_menu_entry",
    OdooSelectors.SUBMENU_ITEM: ".o_menu_entry_lvl_2, .o_menu_entry_lvl_3",
    OdooSelectors.VIEW_SWITCHER: ".o_cp_switch_buttons button",
    OdooSelectors.BUTTON_CREATE: "button[name='create'], button.o_form_button_create, button.o_list_button_add",
    OdooSelectors.BUTTON_SAVE: "button[name='save'], button.o_form_button_save",
    OdooSelectors.BUTTON_EDIT: "button[name='edit'], button.o_form_button_edit",
    OdooSelectors.BUTTON_DISCARD: "button[name='cancel'], button.o_form_button_cancel",
    OdooSelectors.BUTTON_DELETE: "button[name='delete'], button.o_form_button_delete",
    OdooSelectors.BUTTON_ACTION: ".o_cp_action_menus button",
    OdooSelectors.SEARCH_INPUT: ".o_searchview_input",
    OdooSelectors.SEARCH_CLEAR: ".o_searchview_facet_remove",
    OdooSelectors.PAGER_NEXT: ".o_pager_next",
    OdooSelectors.PAGER_PREV: ".o_pager_previous",
    OdooSelectors.PAGER_INFO: ".o_pager_counter",
    OdooSelectors.LIST_ROW: ".o_data_row",
    OdooSelectors.LIST_CELL: ".o_data_cell",
    OdooSelectors.LIST_CHECKBOX: ".o_list_record_selector input",
    OdooSelectors.FORM_FIELD: ".o_field_widget",
    OdooSelectors.FORM_TAB: ".o_notebook_tabs .nav-link",
    OdooSelectors.KANBAN_CARD: ".o_kanban_record",
    OdooSelectors.KANBAN_COLUMN: ".o_kanban_group",
    OdooSelectors.MODAL: ".modal-dialog, .o_dialog",
    OdooSelectors.NOTIFICATION: ".o_notification, .toast",
    OdooSelectors.LOADING: ".o_loading, .o_web_client_loading",
    OdooSelectors.BREADCRUMB: ".o_breadcrumb",
    OdooSelectors.STATUSBAR: ".o_statusbar_buttons",
    OdooSelectors.DROPDOWN: ".o_dropdown_menu, .dropdown-menu",
    OdooSelectors.MANY2ONE: ".o_field_many2one input, .o_field_widget[name] input",
    OdooSelectors.BINARY_UPLOAD: ".o_form_binary_file, input[type='file']",
    OdooSelectors.DATEPICKER: ".o_datepicker_input, .o_datepicker",
}

SELECTORS_V18: Dict[str, str] = {
    OdooSelectors.MENU_ITEM: ".o_menu_entry, .o_navbar_menu_item",
    OdooSelectors.SUBMENU_ITEM: ".o_menu_entry_lvl_2, .o_menu_entry_lvl_3, .o_submenu_item",
    OdooSelectors.VIEW_SWITCHER: ".o_cp_switch_buttons button, [data-view-type]",
    OdooSelectors.BUTTON_CREATE: "button[name='create'], button[data-hotkey='c']:has-text('New')",
    OdooSelectors.BUTTON_SAVE: "button[name='save'], button[data-hotkey='s']:has-text('Save')",
    OdooSelectors.BUTTON_EDIT: "button[name='edit'], button[data-hotkey='e']:has-text('Edit')",
    OdooSelectors.BUTTON_DISCARD: "button[name='cancel'], button[data-hotkey='d']:has-text('Discard')",
    OdooSelectors.BUTTON_DELETE: "button[name='delete'], button:has-text('Delete')",
    OdooSelectors.BUTTON_ACTION: ".o_cp_action_menus button, .o_dropdown_toggler",
    OdooSelectors.SEARCH_INPUT: ".o_searchview_input, input[placeholder*='Search']",
    OdooSelectors.SEARCH_CLEAR: ".o_searchview_facet_remove, .o_facet_remove",
    OdooSelectors.PAGER_NEXT: ".o_pager_next, button[data-pager='next']",
    OdooSelectors.PAGER_PREV: ".o_pager_previous, button[data-pager='prev']",
    OdooSelectors.PAGER_INFO: ".o_pager_counter, .o_pager_status",
    OdooSelectors.LIST_ROW: ".o_data_row, tr.o_data_row",
    OdooSelectors.LIST_CELL: ".o_data_cell, td.o_data_cell",
    OdooSelectors.LIST_CHECKBOX: ".o_list_record_selector input, input[type='checkbox']",
    OdooSelectors.FORM_FIELD: ".o_field_widget, [data-field]",
    OdooSelectors.FORM_TAB: ".o_notebook_tabs .nav-link, .nav-tabs .nav-link",
    OdooSelectors.KANBAN_CARD: ".o_kanban_record, .o_kanban_record_card",
    OdooSelectors.KANBAN_COLUMN: ".o_kanban_group, .o_kanban_column",
    OdooSelectors.MODAL: ".modal-dialog, .o_dialog, .o_modal",
    OdooSelectors.NOTIFICATION: ".o_notification, .toast, .o_alert",
    OdooSelectors.LOADING: ".o_loading, .o_web_client_loading, [aria-busy='true']",
    OdooSelectors.BREADCRUMB: ".o_breadcrumb, .breadcrumb",
    OdooSelectors.STATUSBAR: ".o_statusbar_buttons, .o_form_statusbar",
    OdooSelectors.DROPDOWN: ".o_dropdown_menu, .dropdown-menu, .o_menu",
    OdooSelectors.MANY2ONE: ".o_field_many2one input, [data-type='many2one'] input",
    OdooSelectors.BINARY_UPLOAD: ".o_form_binary_file, input[type='file'], .o_binary_file",
    OdooSelectors.DATEPICKER: ".o_datepicker_input, .o_datepicker, input[type='date']",
}

SELECTORS_V19: Dict[str, str] = {
    OdooSelectors.MENU_ITEM: ".o_menu_entry, .o_navbar_menu_item, [data-menu]",
    OdooSelectors.SUBMENU_ITEM: ".o_menu_entry_lvl_2, .o_menu_entry_lvl_3, .o_submenu_item, [data-submenu]",
    OdooSelectors.VIEW_SWITCHER: ".o_cp_switch_buttons button, [data-view-type], .o_view_switcher button",
    OdooSelectors.BUTTON_CREATE: "button[name='create'], button[data-hotkey='c']:has-text('New'), [data-action='create']",
    OdooSelectors.BUTTON_SAVE: "button[name='save'], button[data-hotkey='s']:has-text('Save'), [data-action='save']",
    OdooSelectors.BUTTON_EDIT: "button[name='edit'], button[data-hotkey='e']:has-text('Edit'), [data-action='edit']",
    OdooSelectors.BUTTON_DISCARD: "button[name='cancel'], button[data-hotkey='d']:has-text('Discard'), [data-action='cancel']",
    OdooSelectors.BUTTON_DELETE: "button[name='delete'], button:has-text('Delete'), [data-action='delete']",
    OdooSelectors.BUTTON_ACTION: ".o_cp_action_menus button, .o_dropdown_toggler, [data-action-menu]",
    OdooSelectors.SEARCH_INPUT: ".o_searchview_input, input[placeholder*='Search'], [data-search-input]",
    OdooSelectors.SEARCH_CLEAR: ".o_searchview_facet_remove, .o_facet_remove, [data-clear-search]",
    OdooSelectors.PAGER_NEXT: ".o_pager_next, button[data-pager='next'], [data-pager-action='next']",
    OdooSelectors.PAGER_PREV: ".o_pager_previous, button[data-pager='prev'], [data-pager-action='previous']",
    OdooSelectors.PAGER_INFO: ".o_pager_counter, .o_pager_status, [data-pager-info]",
    OdooSelectors.LIST_ROW: ".o_data_row, tr.o_data_row, [data-row]",
    OdooSelectors.LIST_CELL: ".o_data_cell, td.o_data_cell, [data-cell]",
    OdooSelectors.LIST_CHECKBOX: ".o_list_record_selector input, input[type='checkbox'], [data-checkbox]",
    OdooSelectors.FORM_FIELD: ".o_field_widget, [data-field], [data-field-name]",
    OdooSelectors.FORM_TAB: ".o_notebook_tabs .nav-link, .nav-tabs .nav-link, [data-tab]",
    OdooSelectors.KANBAN_CARD: ".o_kanban_record, .o_kanban_record_card, [data-kanban-card]",
    OdooSelectors.KANBAN_COLUMN: ".o_kanban_group, .o_kanban_column, [data-kanban-column]",
    OdooSelectors.MODAL: ".modal-dialog, .o_dialog, .o_modal, [data-modal]",
    OdooSelectors.NOTIFICATION: ".o_notification, .toast, .o_alert, [data-notification]",
    OdooSelectors.LOADING: ".o_loading, .o_web_client_loading, [aria-busy='true'], [data-loading]",
    OdooSelectors.BREADCRUMB: ".o_breadcrumb, .breadcrumb, [data-breadcrumb]",
    OdooSelectors.STATUSBAR: ".o_statusbar_buttons, .o_form_statusbar, [data-statusbar]",
    OdooSelectors.DROPDOWN: ".o_dropdown_menu, .dropdown-menu, .o_menu, [data-dropdown]",
    OdooSelectors.MANY2ONE: ".o_field_many2one input, [data-type='many2one'] input, [data-widget='many2one'] input",
    OdooSelectors.BINARY_UPLOAD: ".o_form_binary_file, input[type='file'], .o_binary_file, [data-type='binary']",
    OdooSelectors.DATEPICKER: ".o_datepicker_input, .o_datepicker, input[type='date'], [data-type='date']",
}

SELECTORS_BY_VERSION: Dict[int, Dict[str, str]] = {
    16: SELECTORS_V16,
    17: SELECTORS_V17,
    18: SELECTORS_V18,
    19: SELECTORS_V19,
}


def get_selectors(version: int) -> OdooSelectors:
    return OdooSelectors(version=version)

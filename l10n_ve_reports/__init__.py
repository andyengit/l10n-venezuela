# -*- coding: utf-8 -*-

from . import models
from . import controllers
from . import wizard


def set_periodicity_journal_on_companies(env):
    """Set periodicity journal on companies."""
    for company in env['res.company'].search([]):
        misc_journal = company._get_default_misc_journal()
        if misc_journal:
            company.account_tax_periodicity_journal_id = misc_journal
            if hasattr(misc_journal, 'show_on_dashboard'):
                misc_journal.show_on_dashboard = True


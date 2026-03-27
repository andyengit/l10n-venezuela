DELETE FROM ir_config_parameter
WHERE key IN (
    'l10n_ve_edi_tfhka.username',
    'l10n_ve_edi_tfhka.password'
);

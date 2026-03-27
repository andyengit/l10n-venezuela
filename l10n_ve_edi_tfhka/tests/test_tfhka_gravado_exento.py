from odoo.tests.common import TransactionCase


class TestTfhkaGravadoExento(TransactionCase):
    def test_gravado_exento_cierra_subtotal_tras_reconciliar_buckets(self):
        move = self.env["account.move"].new({})
        cur = self.env.company.currency_id
        buckets = {
            ("A", 31.0): {"base": 4666.01, "tax": 1446.46},
            ("E", 0.0): {"base": 4666.01, "tax": 0.0},
            ("G", 16.0): {"base": 4666.01, "tax": 746.56},
            ("R", 8.0): {"base": 4666.03, "tax": 373.28},
        }
        subtotal = 18664.06
        gravado, exento = move._tfhka_gravado_exento_from_buckets(
            buckets, cur, subtotal_target=subtotal
        )
        self.assertAlmostEqual(gravado + exento, subtotal, places=2)
        self.assertAlmostEqual(gravado, 13998.05, places=2)
        self.assertAlmostEqual(exento, 4666.01, places=2)

    def test_gravado_exento_sin_subtotal_target_usa_suma_cruda(self):
        move = self.env["account.move"].new({})
        cur = self.env.company.currency_id
        buckets = {
            ("G", 16.0): {"base": 100.0, "tax": 16.0},
            ("E", 0.0): {"base": 50.0, "tax": 0.0},
        }
        gravado, exento = move._tfhka_gravado_exento_from_buckets(buckets, cur)
        self.assertAlmostEqual(gravado, 100.0, places=2)
        self.assertAlmostEqual(exento, 50.0, places=2)

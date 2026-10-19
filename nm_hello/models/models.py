# from odoo import models, fields, api


# class nm_hello(models.Model):
#     _name = 'nm_hello.nm_hello'
#     _description = 'nm_hello.nm_hello'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100


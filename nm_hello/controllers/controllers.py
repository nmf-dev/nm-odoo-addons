# from odoo import http


# class NmHello(http.Controller):
#     @http.route('/nm_hello/nm_hello', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/nm_hello/nm_hello/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('nm_hello.listing', {
#             'root': '/nm_hello/nm_hello',
#             'objects': http.request.env['nm_hello.nm_hello'].search([]),
#         })

#     @http.route('/nm_hello/nm_hello/objects/<model("nm_hello.nm_hello"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('nm_hello.object', {
#             'object': obj
#         })


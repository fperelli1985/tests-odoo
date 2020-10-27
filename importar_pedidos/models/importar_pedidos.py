# -*- coding: utf-8 -*-

import json
import datetime
from odoo import models, fields, api, exceptions

class ImportarPedidos(models.TransientModel):
    _name = 'importarpedidos.wizard'
    _description = "Importacion de Pedidos mediante archivos de formato JSON"

    archivo = fields.Binary(string="Archivo JSON")

    def importar_json(self):
        #datos = json.load(self.archivo)
        archivo_nombre = "C:/Sistemas/Proyectos/Web/prueba/importar_pedidos/sample.json"
        with open(archivo_nombre) as datos_archivo:
            datos = json.load(datos_archivo)
        datos_pedido = datos['data']

        # Cliente      
        cliente_datos = datos_pedido['customer']
        cliente_direccion = cliente_datos['address']
        provincia = self.env['res.country.state'].search([('name', '=', cliente_direccion['province'])])
        pais = self.env['res.country'].search([('code', '=', cliente_direccion['country_code'])])
        cliente_nombre = u'%s %s' % (cliente_datos['name'], cliente_datos['surname'])
        cliente = self.env['res.partner'].create({
            'name': cliente_nombre,
            'phone': cliente_datos['phone'],
            'email': cliente_datos['email'],
            'street': cliente_direccion['street'],            
            'city': cliente_direccion['city'],
            'state_id': provincia.id,
            'zip': cliente_direccion['postal_code'],
            'country_id': pais.id,
        })

        ###
        ### Pedido de Venta
        ###

        # Lineas del Pedido
        lineas_datos = datos_pedido['lines']
        pedido_lineas = []
        for linea in lineas_datos:
            producto = self.env['product.product'].search([('default_code', '=', linea['sku'])], limit=1)
            if not producto:
                producto_plantilla = self.env['product.template'].create({
                    'name': linea['name'].encode('utf-8'),
                    'default_code': linea['sku'],                    
                    'type': 'consu',
                    'list_price': linea['price_unit'],
                })
                if producto_plantilla:
                    producto = self.env['product.product'].create({
                        'product_tmpl_id': producto_plantilla.id,
                        'default_code': linea['sku'],
                        'barcode': linea['barcode'],
                    })
                    if not producto:
                        raise exceptions.ValidationError('Error al dar de alta Producto')
                else:
                    raise exceptions.ValidationError('Error al dar de alta Plantilla de Producto')

            pedido_lineas.append([0, False, {
                'product_id': producto.id,
                'product_uom_qty': linea['units'],
                'price_unit': linea['price_unit'],
            }])        

        # La idea era poder buscar a partir de la clave 'payment_method', para ver si ya existe.
        # Habría que ver la lógica cuando no existe, dado que este campo puede o no crearse libremente para cada pedido
        #termino_pago = self.env['account.payment.term'].search([('name', 'like', datos_pedido['payment_method'])], limit=1)
        
        fecha_formateada = datos_pedido['date'].replace('T', ' ')
        fecha = datetime.datetime.strptime(fecha_formateada[0:-5], "%Y-%m-%d %H:%M:%S")
        # Encabezado del Pedido
        pedido = self.env['sale.order'].create({
            'user_id': self.env.uid,
            'partner_id': cliente.id,
            'partner_invoice_id': cliente.id,
            'date_order': fecha,
            'order_line': pedido_lineas,
            'state': datos_pedido['status'],
        })
        
        if not pedido:
            return exceptions.ValidationError('Error al crear Pedido')
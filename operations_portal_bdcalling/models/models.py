# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
import logging
from odoo import models, fields, api
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class EmployeeOrderDetails(models.Model):
    _name = 'project.operation'
    _description = 'Project Operation'
    _inherit = ['mail.thread', 'mail.activity.mixin']


    employee_id = fields.Many2one(
        'hr.employee', 
        string='Employee', 
        default=lambda self: self.env.user.employee_ids[:1] if self.env.user.employee_ids else False,
        tracking=True
    )
    employee_id_barcode = fields.Char(related='employee_id.barcode', string='Employee ID', store=True)
    employee_name = fields.Char(related='employee_id.name', string='Employee Name', store=True)
    user_id = fields.Many2one(related='employee_id.user_id', string='User', store=True)
    company_name = fields.Char(related='employee_id.company_id.name', string='Company', store=True)

    so_id = fields.Char(string='Sale Order')
    order_id = fields.Many2one('sale.order', string='Order ID')
    order_link = fields.Char(string='Order Link')
    order_status = fields.Selection([
        ('nra', 'NRA'),
        ('wip', 'WIP'),
        ('delivered', 'Delivered'),
        ('complete', 'Complete'),
        ('cancelled', 'Cancelled'),
        ('revisions', 'Revisions'),
        ('issues', 'Issues'),
    ], string='Order Status', default='nra', tracking=True)

    project = fields.Char(string='Project')
    partner_id = fields.Many2one('res.partner', string='Partner')
    instruction_sheet_link = fields.Char(string='Instructions Sheet Link')
    
    percentage = fields.Selection([
        ('0', '0%'),
        ('3', '3%'),
        ('5', '5%'),
        ('10', '10%'),
        ('20', '20%'),
    ], string='Percentage')
    operation_status = fields.Selection(
        selection=[
            ('nra', 'NRA'),
            ('wip', 'WIP'),
            ('delivered', 'Delivered'),
            ('complete', 'Complete'),
            ('cancelled', 'Cancelled'),
            ('revisions', 'Revisions'),
            ('issues', 'Issues')
        ],
        string='Operation Status',
        default='nra'  
    )
    employee_barcode = fields.Char(string="Badge ID")
    monetary_value = fields.Float(string='Monetary Value')
    special_remarks = fields.Text(string='Special Remarks')
    date = fields.Date(string='Date', default=fields.Date.context_today)
    company_id = fields.Many2one('res.company', string="Company")
    client_id = fields.Many2one('res.partner', string="Client Name")
    instruction_sheet_link = fields.Char(string="Instruction Sheet Link")
    revision_count = fields.Integer(
        string='Revision Count',
        default=0
    )
    sales_amount_ = fields.Float(
        string='Sales Amount',
        store=True,
    )
    percentage_ = fields.Float(
        string='Percentage',
        store=True
    )
    delivery_amount = fields.Float(string='Delivery Amount')
    monetary_value = fields.Float(
        string='Monetary Value'
    )
    remaining_value = fields.Float(string='Remaining Value', default=0.0, store=True)

    assigned_team_id = fields.Many2one('bd.assign.team', string='Team Name')
    team_members_list = fields.Many2one('hr.employee', string='Team Member')
    @api.onchange('assigned_team_id')
    def _onchange_assigned_team(self):

        for rec in self:
            if rec.assigned_team_id:
                return {
                    'domain': {
                        'team_members_list': [('id', 'in', rec.assigned_team_id.members_ids.ids)]
                    }
                }
            
            else:
                return {
                    'domain': {
                        'team_members_list': []
                    }
                }
            

    @api.onchange("team_members_list")
    def team_member(self):
        self.employee_barcode = self.team_members_list.barcode
        self.company_id = self.team_members_list.company_id 

 
            

    @api.model
    def create(self, vals):
        record = super(EmployeeOrderDetails, self).create(vals)
        if record.order_id:
            last_operation = self.search(
                [('order_id', '=', record.order_id.id)],
                order='id desc', limit=2
            )
            if len(last_operation) > 1:
                previous_remaining = last_operation[1].remaining_value
                record.remaining_value = previous_remaining - record.monetary_value
            else:
                record.remaining_value = record.order_id.delivery_amount - record.monetary_value
        return record

    
    def write(self, vals):
        res = super(EmployeeOrderDetails, self).write(vals)

        for record in self:
            if 'monetary_value' in vals and record.order_id:
                operations = self.search([('order_id', '=', record.order_id.id)], order='id asc')
                total_monetary = sum(operations.mapped('monetary_value'))
                record.remaining_value = record.order_id.delivery_amount - total_monetary
            if record.order_id and ('order_status' in vals or 'assigned_team_id' in vals):
                if not self.env.context.get('skip_sync'):
                    update_vals = {}
                    if 'order_status' in vals:
                        update_vals['order_status'] = vals['order_status']
                    if 'assigned_team_id' in vals:
                        update_vals['assign_team_id'] = vals.get('assigned_team_id')
                    if update_vals:
                        record.order_id.with_context(skip_sync=True).write(update_vals)
        return res

            
    @api.onchange("order_id")
    def onchange_order_id(self):
        if self.order_id:
            self.client_id = self.order_id.partner_id
            self.instruction_sheet_link = self.order_id.instruction_sheet_link
            self.order_status = self.order_id.order_status
            self.special_remarks = self.order_id.special_remarks
            self.assigned_team_id = self.order_id.assign_team_id
            self.sales_amount_ = self.order_id.sales_amount
            self.percentage_ = self.order_id.percentage
            self.delivery_amount = self.order_id.delivery_amount
            self.so_id = self.order_id.name 

            last_operation = self.search(
                [('order_id', '=', self.order_id.id)],
                order='id desc',
                limit=1
            )
            if last_operation:
                self.remaining_value = last_operation.remaining_value
            else:
                self.remaining_value = self.order_id.delivery_amount
        else:
            self.client_id = False
            self.remaining_value = 0.0

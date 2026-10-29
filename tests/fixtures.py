"""Synthetic test transactions only; no customer records."""
import copy

def discount(amount):
    return {'DiscountId': 9001, 'Amount': amount, 'EmployeeId': 9001, 'ManagerId': 9002, 'DiscountName': 'SYNTHETIC_DISCOUNT'}

def item(sequence, gross, sold, discounts):
    return {'ItemId': 9001, 'Quantity': 1, 'GrossPrice': gross, 'SoldPrice': sold, 'EmployeeId': 9001, 'RevenueCenterId': 9001, 'OrderTime': '2099-01-01T12:00:00', 'Seat': 1, 'Sequence': sequence, 'ParentSequence': 0, 'PosSourceId': 1, 'ItemName': 'SYNTHETIC_ITEM', 'ItemPLU': 9001, 'ItemMajorCatId': 1, 'ItemMajorCatName': 'SYNTHETIC', 'ItemSubCatId': 1, 'ItemSubCatName': 'SYNTHETIC', 'Discounts': discounts}

def payment(amount, gratuity, card=True):
    return {'PaymentCategoryId': 9001 if card else 9002, 'Amount': amount, 'Gratuity': gratuity, 'EmployeeId': 9001, 'PosSourceId': 1, 'PayCatNo': 1, 'PayCatName': 'VISA' if card else 'CASH', 'IsCreditCard': card, 'IsGiftCard': False, 'IsGiftCert': False, 'IsPettyCash': False, 'IsNonPOS': False, 'IsCashDebit': False}

def ticket(identifier):
    return {'Id': identifier, 'LocationId': 9001, 'BusinessDate': '2099-01-01', 'TableName': 'SYNTHETIC', 'OpenTime': '2099-01-01T12:00:00', 'CloseTime': '2099-01-01T12:30:00', 'TrafficCount': 1, 'ServiceCharge': 0, 'LoyaltyId': None, 'RevenueCenterId': 9001, 'Tax': [{'TaxCategoryId': 1, 'Amount': 1.0, 'TaxCategoryName': 'SYNTHETIC_TAX'}], 'Discounts': [discount(1.0)], 'Payments': [payment(15.0, -2.0)], 'ItemsSold': [item(1, 10.0, 8.0, [discount(2.0)]), item(2, 5.0, 5.0, [])], 'Voids': [{'ItemId': 9001, 'Quantity': 1, 'Amount': 3.0, 'EmployeeId': 9001, 'ManagerId': 9002, 'VoidCategoryId': 1, 'VoidCategoryName': 'SYNTHETIC_VOID', 'ItemName': 'SYNTHETIC_ITEM', 'ItemPLU': 9001}]}

def dimensions():
    return {
        "locations/locations.json": [{"Id":9001,"Name":"SYNTHETIC_LOCATION","OpenDate":"2099-01-01","ClosedDate":None,"TimeZoneName":"UTC"}],
        "items/items.json": [{"Id":9001,"Name":"SYNTHETIC_ITEM","Plu":9001,"SalesCategoryId":1,"ExternalId":None}],
        "revenue_centers/revenueCenters.json": [{"Id":9001,"Name":"SYNTHETIC_CHANNEL_A"},{"Id":9002,"Name":"SYNTHETIC_CHANNEL_B"}],
        "employees/employees.json": [{"Id":i,"LocationId":9001,"HomeLocationId":9001,"Deleted":False} for i in [9001,9002]]}

def initial():
    first,second=ticket(9001),ticket(9002)
    second.update({"Discounts":[],"Payments":[payment(22.,0.,False)],"ItemsSold":[item(1,20.,20.,[])],"Voids":[]})
    second["Tax"][0]["Amount"]=2.
    return [first,second]+[ticket(i) for i in range(9003,9041)]

def changed():
    rows=initial();corrected=copy.deepcopy(rows[0])
    corrected.update({"RevenueCenterId":9002,"Discounts":[],"Voids":[],"ItemsSold":[item(1,14.,14.,[])],"Payments":[payment(16.,-1.)]})
    corrected["ItemsSold"][0].update({"EmployeeId":9002,"RevenueCenterId":9002})
    corrected["Payments"][0]["EmployeeId"]=9002
    incomplete=ticket(9999)
    incomplete.update({"BusinessDate":"2099-01-02","ItemsSold":[],"Payments":[],"Discounts":[],"Tax":[],"Voids":[]})
    # Ticket 9002 is deliberately omitted: default upsert must retain it.
    return [corrected]+rows[2:], [incomplete]

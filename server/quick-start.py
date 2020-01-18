from azure.servicebus import ServiceBusService, Message, Topic, Rule, DEFAULT_RULE_NAME

bus_service = ServiceBusService(
    service_namespace='licenseplatepublisher',
    shared_access_key_name='ConsumeReads',
    shared_access_key_value='VNcJZVQAVMazTAfrssP6Irzlg/pKwbwfnOqMXqROtCQ=')


msg = bus_service.receive_subscription_message('licenseplateread', 'eG4y7VYFse8NvW53', peek_lock=True)

print(msg.body)
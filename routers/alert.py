from snmp import schemas

async def device_alert(request: schemas.DeviceMetrics):

    if request.status != "success":
        #device unreachble
        pass

    if request.cpu_utilization > 90 :
        #warning critical
        pass
    elif request.cpu_utilization > 70 :
        #gave warning
        pass

    if request.memory_utilization > 95 :
        #warning critical
        pass
    elif request.memory_utilization > 80 :
        #gave warning
        pass

    
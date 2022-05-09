"""
elif method == 'park_closest':
max_occ = 5 * max_occ
fleet = traci.vehicle.getTaxiFleet(0)

for assigned_taxi_stack in assigned_taxis.values():
    for a in assigned_taxi_stack:
        if traci.vehicle.isStoppedParking(a):
            assigned_taxi_stack.remove(a)

fleet = [f for f in fleet if f not in [a for _a in assigned_taxis.values() for a in _a]]

# stops = traci.parkingarea.getIDList()

prt_stops = ['Hotel', 'Station', 'Hospital']  # [stop for stop in stops if 'Parking' in stop]
# target_edges = {'Hotel': 'gneE200', 'Station': 'gneE96', 'Hospital': 'gneE99', 'depot': 'gneE158'}
depot = 'depot'  # [stop for stop in stops if 'depot' in stop][0]

stop_assigned_parkers = defaultdict(lambda: 0)

parkingtargets = [traci.vehicle.getRoute(v)[-1] for v in fleet if
                  v not in (traci.vehicle.getTaxiFleet(1) + traci.vehicle.getTaxiFleet(2))]

for stop in prt_stops:
    stop_assigned_parkers[stop] = len(assigned_taxis[stop]) + traci.parkingarea.getVehicleCount(stop)

# for stop in prt_stops:
#    stop_assigned_parkers[stop] = len([i for i in parkingtargets if i == stop])

for taxi in fleet:
    found_parking = 0
    if not traci.vehicle.isStoppedParking(taxi):
        min_dist = float("inf")
        for stop in prt_stops:

            # TODO: Better distance calculation
            tmp_target = traci.vehicle.getRoute(taxi)[-1]
            try:
                traci.vehicle.changeTarget(vehID=taxi, edgeID=stop)
                dist_to_stop = traci.vehicle.getDrivingDistance(vehID=taxi, edgeID=stop, pos=0)
                traci.vehicle.changeTarget(vehID=taxi, edgeID=tmp_target)
            except traci.exceptions.TraCIException:
                pass

            if dist_to_stop < 0:
                break
            if dist_to_stop < min_dist:
                if stop_assigned_parkers[stop] < max_occ:
                    found_parking = 1
                    min_dist = dist_to_stop
                    new_destination = stop
                    # print('assigned new vehicle to stop: ' + stop)
                    # TODO: Evaluate this inside assignment loop

        if found_parking > 0:
            try:
                assigned_taxis[new_destination].append(taxi)
                traci.vehicle.changeTarget(vehID=taxi, edgeID=new_destination)
                traci.vehicle.setParkingAreaStop(vehID=taxi, stopID=new_destination, duration=999999, flags=1)
                stop_assigned_parkers[new_destination] += 1
            except traci.exceptions.TraCIException or traci.exceptions.FatalTraCIError:
                pass

# elif method == ...: Add new methods here

else:
    return None
'''
for stop in prt_stops:
    # stop_assigned_parkers[stop] += traci.parkingarea.getVehicleCount(stop)
#print(stop_assigned_parkers)
'''
"""
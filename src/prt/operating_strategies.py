import traci
import random

rebalanced_veh = {'Station': [], 'Hotel': [], 'Hospital': [], 'depot': []}  # needed for reb. method "park_closest"
nr_at_station = {'Station': 0, 'Hotel': 0, 'Hospital': 0, 'depot': 0}  # needed for reb. method "park_closest"


def dist_to_edge(vehId, edgeId):
    try:
        start_edge = traci.vehicle.getLaneID(vehId)
        start_edge = start_edge[:len(start_edge)-2]
        if start_edge != '':
            stage = traci.simulation.findRoute(fromEdge=start_edge, toEdge=edgeId, vType=traci.vehicle.getTypeID(vehId))
            dist = stage.length
        else:
            tmp_target = traci.vehicle.getRoute(vehId)[-1]  # save the current target to reset later
            try:  # changing target can cause problems and cause traci to crash
                traci.vehicle.changeTarget(vehID=vehId, edgeID=edgeId)
                dist = traci.vehicle.getDrivingDistance(vehID=vehId, edgeID=edgeId, pos=0)
                traci.vehicle.changeTarget(vehID=vehId, edgeID=tmp_target)
            except traci.exceptions.TraCIException as e:
                # do something with the exception here if desired
                pass

    except traci.exceptions.TraCIException as e:
        # parked vehicles might return an empty stage object (= no dist). in that case, try the "old" way.
        # print(e)
        tmp_target = traci.vehicle.getRoute(vehId)[-1]  # save the current target to reset later
        try:  # changing target can cause problems and cause traci to crash
            traci.vehicle.changeTarget(vehID=vehId, edgeID=edgeId)
            dist = traci.vehicle.getDrivingDistance(vehID=vehId, edgeID=edgeId, pos=0)
            traci.vehicle.changeTarget(vehID=vehId, edgeID=tmp_target)
        except traci.exceptions.TraCIException as e:
            # do something with the exception here if desired
            pass
    return dist



def rebalance(method, max_occ=1):
    """
    Rebalances empty vehicles to bus stops according to a specified method
    :param method: Name of the Method/Algorithm/Heuristic according to which the vehicles should be redistributed : String
    :param max_occ: maximum occupancy at which vehicles still wait at the station
    :return: None (if no method is specified, the vehicles will drive random routes when they are not assigned to a customer)
    """
    global rebalanced_veh
    global nr_at_station

    if method == 'random_idling':
        # the taxis idle randomly on their own via the SUMO functionality
        return

    elif method == 'park_in_depot':  # TODO: only works for one hard coded depot right now
        # unoccupied vehicles fo back to the depot
        fleet = traci.vehicle.getTaxiFleet(0)
        stops = traci.parkingarea.getIDList()
        depot = [stop for stop in stops if 'depot' in stop]
        for taxi in fleet:
            if not traci.vehicle.isStoppedParking(taxi):
                try:
                    traci.vehicle.changeTarget(taxi, traci.lane.getEdgeID(traci.parkingarea.getLaneID('depot')))
                    traci.vehicle.setParkingAreaStop(taxi, 'depot', duration=999999, flags=1)
                except traci.exceptions.TraCIException as e:
                    print(e)
                    continue

    elif method == 'park_closest_no_idling':
        # vehicles park in the closest station that is not completely occupied.
        # if they don't find a space, they park in the depot.
        new_idle_veh = []
        max_occ = 5 * max_occ
        prt_stops = ['Hotel', 'Station', 'Hospital']
        # get new idling vehicles
        fleet = traci.vehicle.getTaxiFleet(0)
        veh_ids_sum = []
        for veh_ids in rebalanced_veh.values():
            veh_ids_sum += veh_ids
        veh_ids_sum = list(set(veh_ids_sum))
        for v in fleet:
            if not traci.vehicle.isStoppedParking(v):
                if v not in new_idle_veh:
                    if v not in veh_ids_sum:
                        new_idle_veh.append(v)
        # check if vehicles stopped idling/got booked/left the station...
        for waiting_vehs in rebalanced_veh.values():
            for veh in waiting_vehs:
                try:
                    if traci.vehicle.isStoppedParking(veh):
                        waiting_vehs.remove(veh)
                    if veh in traci.vehicle.getTaxiFleet(1):
                        waiting_vehs.remove(veh)
                except traci.exceptions.TraCIException as e:
                    if 'is not known' in str(e):
                        waiting_vehs.remove(veh)
                    pass
        # calculate total numer of parked AND assigned vehicles for each stop:
        for stop in prt_stops:
            nr_at_station[stop] = traci.parkingarea.getVehicleCount(stop) + len(rebalanced_veh[stop])
        nr_at_station['depot'] = traci.parkingarea.getVehicleCount('depot') + len(rebalanced_veh['depot'])

        # look for the closest parking spot for each vehicle that is new in idle
        for veh in new_idle_veh:
            found_parking = 0  # the vehicle has not found a slot in one of the stations
            min_dist = float("inf")  # set the minimal distance to inf for each vehicle
            for stop in prt_stops:  # check the distance to the stop
                dist_to_stop = dist_to_edge(veh, stop)
                if 0 < dist_to_stop < min_dist:
                    if nr_at_station[stop] < max_occ:
                        found_parking = 1
                        min_dist = dist_to_stop
                        new_destination = stop
                        # TODO: Evaluate this inside assignment loop

            if found_parking > 0:
                try:
                    rebalanced_veh[new_destination].append(veh)
                    traci.vehicle.changeTarget(vehID=veh, edgeID=new_destination)
                    traci.vehicle.setParkingAreaStop(vehID=veh, stopID=new_destination, duration=999999, flags=1)
                    # update total numer of parked AND assigned vehicles for each stop:
                    nr_at_station[new_destination] = traci.parkingarea.getVehicleCount(stop) + len(rebalanced_veh[new_destination])
                    nr_at_station['depot'] = traci.parkingarea.getVehicleCount('depot') + len(rebalanced_veh['depot'])
                except traci.exceptions.TraCIException or traci.exceptions.FatalTraCIError:
                    pass
            else:  # if no space was available in any station, go to depot
                try:
                    rebalanced_veh['depot'].append(veh)
                    traci.vehicle.changeTarget(veh, 'Depot')
                    traci.vehicle.setParkingAreaStop(veh, 'depot', duration=999999, flags=1)
                except traci.exceptions.TraCIException:
                    pass

    elif method == 'park_closest_idling':
        # vehicles park in the closest station that is not completely occupied.
        # if they don't find a space, they idle randomly.
        new_idle_veh = []
        max_occ = 5 * max_occ
        prt_stops = ['Hotel', 'Station', 'Hospital']

        # get new idling vehicles
        fleet = traci.vehicle.getTaxiFleet(0)
        veh_ids_sum = []
        for veh_ids in rebalanced_veh.values():
            veh_ids_sum += veh_ids
        veh_ids_sum = list(set(veh_ids_sum))
        for v in fleet:
            if not traci.vehicle.isStoppedParking(v):
                if v not in new_idle_veh:
                    if v not in veh_ids_sum:
                        new_idle_veh.append(v)
        # check if vehicles stopped idling/got booked/left the station...
        for waiting_vehs in rebalanced_veh.values():
            for veh in waiting_vehs:
                try:
                    if traci.vehicle.isStoppedParking(veh):
                        waiting_vehs.remove(veh)
                    if veh in traci.vehicle.getTaxiFleet(1):
                        waiting_vehs.remove(veh)
                    if veh in traci.vehicle.getTaxiFleet(2):
                        waiting_vehs.remove(veh)
                except traci.exceptions.TraCIException as e:
                    if 'is not known' in str(e):
                        waiting_vehs.remove(veh)
                    pass

        # calculate total numer of parked AND assigned vehicles for each stop:
        for stop in prt_stops:
            nr_at_station[stop] = traci.parkingarea.getVehicleCount(stop) + len(rebalanced_veh[stop])
        nr_at_station['depot'] = traci.parkingarea.getVehicleCount('depot') + len(rebalanced_veh['depot'])

        # look for the closest parking spot for each vehicle that is new in idle
        for veh in new_idle_veh:
            found_parking = 0  # the vehicle has not found a slot in one of the stations
            min_dist = float("inf")  # set the minimal distance to inf for each vehicle
            for stop in prt_stops:  # check the distance to the stop
                dist_to_stop = dist_to_edge(veh, stop)
                if 0 < dist_to_stop < min_dist:
                    if nr_at_station[stop] < max_occ:
                        found_parking = 1
                        min_dist = dist_to_stop
                        new_destination = stop
                        # TODO: Evaluate this inside assignment loop

            if found_parking > 0:
                try:
                    rebalanced_veh[new_destination].append(veh)
                    traci.vehicle.changeTarget(vehID=veh, edgeID=new_destination)
                    traci.vehicle.setParkingAreaStop(vehID=veh, stopID=new_destination, duration=999999, flags=1)
                    # update total numer of parked AND assigned vehicles for each stop:
                    nr_at_station[new_destination] = traci.parkingarea.getVehicleCount(stop) + len(rebalanced_veh[new_destination])
                    nr_at_station['depot'] = traci.parkingarea.getVehicleCount('depot') + len(rebalanced_veh['depot'])
                except traci.exceptions.TraCIException or traci.exceptions.FatalTraCIError:
                    pass


def dispatch(strategy):
    """
    dispatches a taxi to new requests. Multiple strategies can be implemented.
    :param strategy: dispatching method to be chosen : String
    :return:
    """
    free_taxis = traci.vehicle.getTaxiFleet(flag=0)
    reservations = traci.person.getTaxiReservations(1)
    if strategy == "mockup":
        for reservation in reservations:
            try:
                traci.vehicle.dispatchTaxi(random.choice(free_taxis), reservation.id)
            except traci.exceptions.TraCIException:
                pass
    return

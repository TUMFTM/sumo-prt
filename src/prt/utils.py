import traci
import random
import os
import math
import pandas as pd


def reroute_finished_veh():
    """
    reroutes vehicles that have finished their route. Note: this function will probably be redundant in the scope
    of the Bad Hersfeld project since we are using the taxi device.
    :return:
    """
    vids = traci.vehicle.getIDList()
    vids = [v for v in vids if "prt" in v]
    edges = traci.edge.getIDList()
    edges = [e for e in edges if "gne" in e]
    edges = [e for e in edges if ":" not in e]
    for vid in vids:
        # route_ID = "route_" + vid[4:]
        route_ID = 'default'  # TODO: correct this!
        route = traci.route.getEdges(str(route_ID))
        if traci.vehicle.getSpeed(vid) == 0.0:
            stopped = 1
            while stopped:
                try:
                    traci.vehicle.changeTarget(vid, random.choice(edges))
                    stopped = 0
                except traci.exceptions.TraCIException:
                    pass
        if traci.vehicle.getRoadID(vid) == route[-1] and traci.vehicle.getLanePosition(vid) + 10 > traci.lane.getLength(
                traci.vehicle.getRoadID(vid) + '_0'):
            changed_target = 0
            while not changed_target:
                try:
                    traci.vehicle.changeTarget(vid, random.choice(edges))
                    changed_target = 1
                except traci.exceptions.TraCIException:
                    pass
    return


def count_prt_veh():
    """
    counts the number of PRT/Dromos vehicles current in the simulation
    :return: number of vehicles of type PRT : Integer
    """
    veh_ids = traci.vehicle.getIDList()
    prt_ids = [id for id in veh_ids if "prt" in id]
    nr_prt = len(prt_ids)
    return nr_prt


def trips_from_ODM(ODM_file, path_to_ODM=""):
    """
    creates a DataFrame with columns [departure, origin, destination] from an Origin Destination Matrix (ODM). The
    ODM is written in .xlsx and contains the amount of trips in each direction. This number is dispersed over 3600s
    via a Poisson Process and an hourly scaling factor [0,1].
    :param ODM_file: name of the ODM file including ending .xlsx : String
    :param path_to_ODM: path to the file if not in same dir as module utils : String
    :return: a pandas DataFrame with columns [departure, origin, destination] : DataFrame
    """
    odm = df_from_csv(ODM_file, path_to_ODM)
    scaling_factors = list(odm.iloc[0, 6:])
    trips = pd.DataFrame(columns=['departure', 'origin', 'destination'])
    origins = list(odm.index)
    destinations = list(odm)[:4]
    for hour in range(0, len(scaling_factors)):
        for row in range(0, 4):
            for col in range(0, 4):
                if odm.iloc[row, col] != 0:
                    new_trip_times = poisson_process(int(odm.iloc[row, col]*scaling_factors[hour]),\
                                                     int(odm.iloc[row, col]*scaling_factors[hour]))
                    new_trip_times = [x+3600*hour for x in new_trip_times]
                    new_trips = pd.DataFrame(columns=['departure', 'origin', 'destination'])
                    new_trips['departure'] = new_trip_times
                    new_trips['origin'] = origins[row]
                    new_trips['destination'] = destinations[col]
                    trips = pd.concat([trips, new_trips], ignore_index=True)
    return trips


def df_from_csv(ODM_file='odm.csv', path_to_ODM=""):
    """
    converts an Excel sheet to a pandas DataFrame
    :param ODM_file: name of the ODM file including ending .xlsx : String
    :param path_to_ODM: path to the file if not in same dir as module utils : String
    :return: a pandas DataFrame containing the same information as the .xlsx : DataFrame
    """
    if path_to_ODM != '':
        open_file = os.path.join(path_to_ODM, ODM_file)
    else:
        open_file = os.path.join(ODM_file)
    df = pd.read_csv(open_file, index_col=0, sep=';')
    return df


def poisson_process(lambda_var, num_events):  # TODO something seems to be slightly off here - check again!
    """
    this function models the Poisson Process that enables us to distribute hourly trip numbers over an interval of
    time. This interval is 3600s in our case. More information can be found in the source below.
    source: https://timeseriesreasoning.com/contents/poisson-process/
    :param lambda_var: incidence rate : Integer
    :param num_events: number of events per interval : Integer
    :return: absolute times of each arrival : List
    """
    lambda_var = lambda_var
    num_events = num_events
    event_num = []
    inter_event_times = []
    event_times = []
    event_time = 0

    for i in range(num_events):
        event_num.append(i)
        # Get a random probability value from the uniform distribution's PDF
        n_rand = random.random()
        # Generate the inter-event time from the exponential distribution's CDF using the Inverse-CDF technique
        inter_event_time = -math.log(1.0 - n_rand) / lambda_var
        inter_event_times.append(inter_event_time)
        # Add the inter-event time to the running sum to get the next absolute event time
        event_time = (event_time + inter_event_time)
        event_times.append(event_time)
    event_times = [math.floor(time*3600) for time in event_times]
    return event_times


def spawn_persons(step, trips):
    """
    checks if the current simulation step yields a trip. if so, it adds a person to traci and appends a driving
    stage with a taxi to it.
    :param step: current simulation step : Integer
    :param trips: the list of all trips that were calculated for the simulation runtime : DataFrame
    :return:
    """
    if int(step) in list(trips['departure']):
        departure_index = trips.loc[trips['departure'] == step].index.tolist()
        # add person
        p_at_t = 0
        for index in departure_index:
            pers_id = "prt_user_%s" % int(step) + ("_%s" % p_at_t if p_at_t > 0 else "")
            try:
                traci.person.add(personID=pers_id, edgeID=trips.loc[index, 'origin'], pos=-1)
                traci.person.appendWalkingStage(personID=pers_id, edges=[trips.loc[index, 'origin']], arrivalPos=-1, stopID=trips.loc[index, 'origin']+'_stop')
                traci.person.appendDrivingStage(personID=pers_id, toEdge=trips.loc[index, 'destination'] + "_arrival",
                                                stopID=trips.loc[index, 'destination']+'_arrival_stop', lines='taxi')
                p_at_t += 1
            except traci.TraCIException as e:
                print(e)
                pass
    return




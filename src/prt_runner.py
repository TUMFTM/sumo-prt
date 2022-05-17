#!/usr/bin/env python3
import sys
import os

sys.path += [os.path.join(os.environ["SUMO_HOME"], "tools")]

import sumolib  # noqa
from sumolib import checkBinary  # noqa
import traci  # noqa
from prt import utils, merging_control, operating_strategies  # noqa


def get_options():
    argParser = sumolib.options.ArgumentParser()
    argParser.add_argument("--nogui", action="store_true",
                           default=False, help="run the commandline version of sumo")
    argParser.add_argument("--duration", type=int, default=30000,
                           help="simulation duration in seconds")
    argParser.add_argument("--stop-line", type=float, default=-15.,
                           help="stop line distance in meters")
    argParser.add_argument("--v2i-range", type=float, default=200.,
                           help="communication distance in meters")
    argParser.add_argument("--time-step", type=float, default=1.,
                           help="simulation step size")
    argParser.add_argument("--config", default="prt.sumocfg", help="sumo config to run")
    return argParser.parse_args()


def runner():
    """
    this function starts traci and runs the preconfigured traffic in Bad Hersfeld as well as the PRT/Dromos
    application. It initializes the compressors and calls methos from the modules utils and operating_strategies.
    :return:
    """
    options = get_options()
    # this script has been called from the command line. It will start sumo as a
    # server, then connect and run
    if options.nogui:
        sumoBinary = checkBinary('sumo')
    else:
        sumoBinary = checkBinary('sumo-gui')
    traci.start([sumoBinary, "-c", options.config, "--ignore-route-errors", "--collision.action=remove",
                 "--no-warnings", "--device.taxi.idle-algorithm=randomCircling",
                 "--device.taxi.dispatch-algorithm=greedyClosest"])
    # as dispatch algo, we can also use the ones from SUMO, e.g. greedy.
    # When using 'traci', you must un-comment line 64
    vmax = traci.vehicletype.getMaxSpeed("dromos")
    max_accel = traci.vehicletype.getAccel("dromos")
    veh_len = traci.vehicletype.getLength("dromos")
    time_gap = traci.vehicletype.getTau("dromos")
    step_multiplier = 1 / options.time_step

    step = 0

    trips = utils.trips_from_ODM('odm.csv', 'cfg')

    TL_ids = traci.trafficlight.getIDList()
    smart_zipper_ids = [sz_id for sz_id in TL_ids if "sz" in sz_id]
    smart_zippers = []
    for zipper_id in smart_zipper_ids:
        smart_zippers.append(merging_control.Compressor(zipper_id, options.stop_line, options.v2i_range,
                                                        vmax, max_accel, time_gap, veh_len))

    while step < options.duration:
        traci.simulationStep()

        for zipper in smart_zippers:
            zipper.execution_step(step, step_multiplier)

        if step % step_multiplier == 0:
            # check if trips are occurring in the current step
            utils.spawn_persons(step, trips)
            # dispatch
            # operating_strategies.dispatch('mockup') # un-comment in case you want to use it
            # rebalance
            operating_strategies.rebalance('random_idling')

        step += 1

    traci.close()
    return


if __name__ == "__main__":
    runner()

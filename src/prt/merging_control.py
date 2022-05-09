import traci
import math


def compute_ETA(current_speed, target_speed, distance, acceleration, deceleration):
    """
    computes the time of arrival for a car entering the intersection. it does so by calculating the time the car spends
    accelerating (using the differential dependencies of v and a) and the subsequent time of constant velocity.
    The assumption is that each car can either speed up with max. accelereation or slow down with max. deceleration.
    The speedMode is set to 32 (all checks off) while passing the intersection
    :param current_speed: current speed of the vehicle : Float
    :param target_speed: desired speed of the vehicle, logically v max for max. capacity of the intersection : Float
    :param distance: remaining distance to the corssing point of the intersection : Float
    :param acceleration: maximum acceleration of the vehicle : Float
    :param deceleration: maximum deceleration of the vehicle : Float
    :return:
    """
    if current_speed <= target_speed:
        t_acc = (target_speed - current_speed) / acceleration
        dist_acc = 0.5 * acceleration * t_acc ** 2
        dist_rem = distance - dist_acc
        t_v_const = dist_rem / target_speed
        t_total = t_acc + t_v_const
    else:
        t_acc = (target_speed - current_speed) / deceleration
        dist_acc = 0.5 * deceleration * t_acc ** 2
        dist_rem = distance - dist_acc
        t_v_const = dist_rem / target_speed
        t_total = t_acc + t_v_const
    return t_total


class Compressor:
    """
    a class that allows for merging controll at intersections
    Attributes:
        id: id of the compressor object : str
        stopline: position of the stopline in regard to the end of the SUMO lane : int
        v2i_range: maximum range of v2i communication, measured from the joining point : int
        vmax: maximum velocity of the vehicles driving on the compressor : float
        amax: maximum acceleration of the vehicles driving on the compressor : float
        dec_max: maximum deceleration of the vehicles driving on the compressor : float
        vehlen: length of the vehicles driving on the compressor : int
        timegap: desired time headway between cars following each other : float
        blocked_slots: time slots that are already reserved for a vehicle : list
        served_veh: IDs of vehicles that have already passed the intersection : list
        cars_slots: slots of cars that have passed the compressor, mainly for debugging : dictionary
        cars_v: velocities of cars that have passed the compressor, mainly for debugging : dictionary
        new_veh: vehicles entering the v2i zone : dictionary
        incomings: incoming edges of the compressor : list
        outgoings: outgoing edges of the compressor : list
    Methods:
        check_new_veh
        serve_new_veh
        check_served_veh
        clean_blocked_slots
        execution_step
    """
    def __init__(self, compressor_id, stopline, v2i_range, vmax, amax, timegap, vehlen):
        """
        initializer of the class, constructs the attributes
        :param compressor_id: id of the comressor : String
        :param stopline: position of the stopline in regard to the end of the SUMO lane : int
        :param v2i_range: maximum range of v2i communication, measured from the joining point : int
        :param vmax: maximum velocity of the vehicles driving on the compressor : float
        :param amax: maximum acceleration of the vehicles driving on the compressor : float
        :param timegap: desired time headway between cars following each other : float
        :param vehlen: length of the vehicles driving on the compressor : int
        """
        self.id = compressor_id
        self.stopline = stopline
        self.v2i_range = v2i_range
        self.vmax = vmax
        self.amax = amax
        self.dec_max = amax  # TODO: remodel parameter
        self.vehlen = vehlen
        self.timegap = timegap
        self.blocked_slots = []
        self.served_veh = []
        self.controlledLinks = traci.trafficlight.getControlledLinks(compressor_id)
        self.cars_slots = {}
        self.cars_v = {}
        self.new_veh = {}
        outLinksTemp = []
        inLinksTemp = []
        for link in self.controlledLinks:
            inLinksTemp.append(link[0][0])
            outLinksTemp.append(link[0][1])
        self.incomings = inLinksTemp
        self.outgoings = outLinksTemp
        self.outgoings = list(dict.fromkeys(self.outgoings))
        for i in range(len(self.outgoings)):
            self.outgoings[i] = self.outgoings[i][:(len(self.outgoings[i]) - 2)]
        for i in range(len(self.incomings)):
            self.incomings[i] = self.incomings[i][:(len(self.incomings[i]) - 2)]
        for i in self.incomings:
            if traci.lane.getLength(i+"_0") < self.v2i_range:
                self.v2i_range = math.floor(traci.lane.getLength(i+"_0"))
                # print("SZ_Nr.: " + self.id + "... range: " + str(self.v2i_range)) # debugging only

    def check_new_veh(self):
        """
        checks if new vehicles have arrived in the v2i zone. If yes, they are stored in the new_veh list to be dealt
        with in another method.
        :return:
        """
        self.new_veh = {}
        for incoming_edge in self.incomings:
            lastStepVehicleIds = traci.edge.getLastStepVehicleIDs(incoming_edge)
            new_vehicles = [x for x in lastStepVehicleIds if x not in self.served_veh]
            for vid in new_vehicles:
                remainingDist = traci.vehicle.getDrivingDistance(vehID=vid, edgeID=incoming_edge, \
                                                                 pos=(traci.lane.getLength(incoming_edge + '_0'))) \
                                - self.stopline
                if remainingDist < self.v2i_range:
                    self.new_veh[vid] = [vid, traci.vehicle.getSpeed(vid), remainingDist, None]  # ID, Speed, Dist, ETA
                    self.served_veh.append(vid)
        return

    def serve_new_veh(self, step, step_multiplier):
        """
        vehicles which have just arrived in the v2i zone are dealt with. Their soonest possible arrival time is calculated
        as well as the respective speed and acceleration. SpeedMode is changed to 32 and speed set.
        :param step: current simulation step : int
        :param step_multiplier: multiplier to calculate back to seconds from the simulation step length
        :return:
        """
        # 0ID, 1 Speed, 2 Dist, 3 ETA
        for vid in self.new_veh:
            traci.vehicle.setSpeedMode(vid, 32)
            ETA = None
            v_current = traci.vehicle.getSpeed(vid)
            desiredETA = compute_ETA(v_current, self.vmax, self.new_veh[vid][2], self.amax, self.dec_max) * \
                         step_multiplier + step
            if len(self.blocked_slots) == 0:
                self.blocked_slots.append(desiredETA)
                ETA = desiredETA
                new_speed = self.vmax
                traci.vehicle.setSpeed(vid, new_speed)
            elif len(self.blocked_slots) >= 1:
                possibleETA = self.blocked_slots[-1] + (self.timegap + (self.vehlen / self.vmax)) * step_multiplier
                if possibleETA < desiredETA:
                    self.blocked_slots.append(desiredETA)
                    ETA = desiredETA
                    new_speed = self.vmax
                    traci.vehicle.setSpeed(vid, new_speed)
                else:
                    self.blocked_slots.append(possibleETA)
                    ETA = possibleETA
                    new_speed = self.new_veh[vid][2] / ((possibleETA - step) / step_multiplier)
                    traci.vehicle.setSpeed(vid, new_speed)
            if new_speed < self.vmax:
                traci.vehicle.setColor(vid, (0, 55, 255))  # blue
            else:
                traci.vehicle.setColor(vid, (0, 255, 0))  # green
            self.cars_v[vid] = new_speed
            self.cars_slots[vid] = ETA
            return

    def check_served_veh(self):
        """
        checks if served vehicles have left the intersection. If yes, they are deleted from the lists and their speedMode
        is set back to 31 (default; the CFM takes over control of the vehicle)
        :return:
        """
        for outgoing_edge in self.outgoings:
            lastStepVehicleIds = traci.edge.getLastStepVehicleIDs(outgoing_edge)
            finished_vehicles = [x for x in lastStepVehicleIds if x in self.served_veh]
            for vid in finished_vehicles:
                # record the vehicle which has arrived at the junction
                traci.vehicle.setColor(vid, (255, 255, 255))  # red
                self.served_veh.remove(vid)
                self.blocked_slots.remove(self.cars_slots[vid])
                del self.cars_slots[vid]
                del self.cars_v[vid]
                # del self.new_veh[vid]
                traci.vehicle.setSpeed(vid, self.vmax)
                traci.vehicle.setSpeedMode(vid, 31)
        return

    def clean_blocked_slots(self, step, step_multiplier):
        """
        sorts the list of blocked time slots and deletes very old slots in case something went wrong
        :param step: current simulation step : int
        :param step_multiplier: multiplier to calculate back to seconds from the simulation step length
        :return:
        """
        self.blocked_slots = sorted(self.blocked_slots)
        self.blocked_slots = [test for test in self.blocked_slots if test < \
                              (step * step_multiplier + self.vmax * 20 * self.timegap)]
        return

    def execution_step(self, step, step_multiplier):
        """
        calls the other methods and therefore executes all functionalities of the compressor class
        :param step: current simulation step : int
        :param step_multiplier: multiplier to calculate back to seconds from the simulation step length
        :return:
        """
        self.check_new_veh()
        self.check_served_veh()
        self.serve_new_veh(step, step_multiplier)
        self.clean_blocked_slots(step, step_multiplier)
        return

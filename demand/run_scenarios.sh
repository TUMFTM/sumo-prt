#!/bin/bash
pushd ../prt_infra
./build.sh
popd
sumo -c ../src/joined.sumocfg -r osm_activitygen_present_no_prt.rou.xml.gz --output-prefix ../osm/outputs/present_ &> present.log &
sumo -c ../src/joined.sumocfg -r osm_activitygen_future_no_prt.rou.xml.gz --output-prefix ../osm/outputs/future_ &> future.log &
sumo -c ../src/joined.sumocfg -r osm_activitygen_future_with_prt.rou.xml.gz --output-prefix ../osm/outputs/prt_ &> prt.log &
wait

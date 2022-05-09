"%SUMO_HOME%/bin/netconvert" -n prt_infra.nod.xml -e prt_infra.edg.xml -t prt_infra.typ.xml -x prt_infra.con.xml -o prt.net.xml
"%SUMO_HOME%/bin/netconvert" -s ../osm/osm_edited.net.xml.gz,prt.net.xml -o joined.net.xml
python net2poly.py -n prt.net.xml -o prt_poly.add.xml
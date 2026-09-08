"""
NetSage AI - Case Dataset Builder
Generates data/cases.csv: 30 Packet-Tracer-style network troubleshooting cases.

Columns:
  case_id, category, severity, symptom, topology_note, show_output,
  expected_fault, osi_layer, concept_tag

show_output is written in a Cisco-IOS-like style on purpose, so that
scripts/rule_checker.py can pattern-match real signals (interface state,
IP/mask lines, VLAN tables, route tables, gateway lines) instead of
just reading English text.
"""
import csv
import os

CASES = [
    # ---------------- VLAN (5) ----------------
    dict(
        case_id="C001", category="VLAN", severity="Medium",
        symptom="PC-A (VLAN 10) can ping its own gateway but cannot reach PC-B (VLAN 20).",
        topology_note="SW1 trunk to R1 (router-on-a-stick), sub-interfaces Gi0/0.10 and Gi0/0.20.",
        show_output=(
            "SW1# show vlan brief\n"
            "VLAN Name       Status  Ports\n"
            "10   Sales      active  Fa0/1, Fa0/2\n"
            "20   Support    active  Fa0/3, Fa0/4\n\n"
            "SW1# show interfaces trunk\n"
            "Port    Mode  Encapsulation  Status     Native vlan\n"
            "Gi0/1   on    802.1q         trunking   1\n"
            "Allowed VLANs on trunk: 1,10\n"
        ),
        expected_fault="VLAN 20 not permitted on the trunk (allowed-vlan list missing 20)",
        osi_layer="Layer 2", concept_tag="trunk-allowed-vlan",
    ),
    dict(
        case_id="C002", category="VLAN", severity="High",
        symptom="All hosts on Fa0/5 lost connectivity after a switch reload; port was previously in VLAN 30.",
        topology_note="Access switch SW2, port Fa0/5 assigned to VLAN 30 (Finance).",
        show_output=(
            "SW2# show vlan brief\n"
            "VLAN Name      Status  Ports\n"
            "1    default    active  Fa0/6, Fa0/7\n"
            "10   Sales      active  Fa0/1\n\n"
            "SW2# show interfaces fa0/5 switchport\n"
            "Administrative Mode: static access\n"
            "Access Mode VLAN: 30 (Inactive)\n"
        ),
        expected_fault="VLAN 30 does not exist on the switch (deleted or never created) -> port is inactive",
        osi_layer="Layer 2", concept_tag="missing-vlan",
    ),
    dict(
        case_id="C003", category="VLAN", severity="Low",
        symptom="New PC plugged into Fa0/8 gets no link light and cannot obtain an IP address.",
        topology_note="Fa0/8 was previously used for a printer that was removed.",
        show_output=(
            "SW1# show interfaces fa0/8\n"
            "FastEthernet0/8 is administratively down, line protocol is down\n"
        ),
        expected_fault="Switchport administratively shut down",
        osi_layer="Layer 1", concept_tag="interface-shutdown",
    ),
    dict(
        case_id="C004", category="VLAN", severity="Medium",
        symptom="Voice VLAN phones register, but PCs behind the phones on the same port cannot reach the LAN.",
        topology_note="Fa0/2 configured with data VLAN 10 and voice VLAN 110.",
        show_output=(
            "SW1# show interfaces fa0/2 switchport\n"
            "Administrative Mode: static access\n"
            "Access Mode VLAN: 1 (default)\n"
            "Voice VLAN: 110 (Active)\n"
        ),
        expected_fault="Data VLAN on the port left at default VLAN 1 instead of VLAN 10",
        osi_layer="Layer 2", concept_tag="voice-data-vlan-mismatch",
    ),
    dict(
        case_id="C005", category="VLAN", severity="Medium",
        symptom="Two access switches; hosts in VLAN 40 on SW1 cannot reach VLAN 40 hosts on SW2.",
        topology_note="SW1 and SW2 connected via a trunk link Gi0/1<->Gi0/1.",
        show_output=(
            "SW1# show interfaces trunk\n"
            "Port   Native vlan   Allowed VLANs\n"
            "Gi0/1  1             1,10,20,40\n\n"
            "SW2# show interfaces trunk\n"
            "Port   Native vlan   Allowed VLANs\n"
            "Gi0/1  99            1,10,20,40\n"
        ),
        expected_fault="Native VLAN mismatch across the trunk (SW1=1, SW2=99) causing CDP/STP issues and dropped untagged traffic",
        osi_layer="Layer 2", concept_tag="native-vlan-mismatch",
    ),

    # ---------------- Gateway (4) ----------------
    dict(
        case_id="C006", category="Gateway", severity="High",
        symptom="PC gets an IP address but cannot ping anything outside its own subnet, including the gateway.",
        topology_note="PC-A on VLAN 10, gateway should be R1 Gi0/0.10 = 192.168.10.1",
        show_output=(
            "PC-A> ipconfig\n"
            "IP Address: 192.168.10.25\n"
            "Subnet Mask: 255.255.255.0\n"
            "Default Gateway: 192.168.10.254\n\n"
            "R1# show ip interface brief\n"
            "Interface        IP-Address      Status   Protocol\n"
            "GigabitEthernet0/0.10  192.168.10.1  up       up\n"
        ),
        expected_fault="Default gateway on PC-A (192.168.10.254) does not match the router sub-interface IP (192.168.10.1)",
        osi_layer="Layer 3", concept_tag="gateway-mismatch",
    ),
    dict(
        case_id="C007", category="Gateway", severity="Medium",
        symptom="PC can ping the gateway address but nothing beyond it.",
        topology_note="R1 Gi0/0 connects to the LAN, Gi0/1 connects toward the WAN/ISP.",
        show_output=(
            "R1# show ip interface brief\n"
            "Interface   IP-Address     Status                  Protocol\n"
            "Gi0/0       192.168.1.1    up                      up\n"
            "Gi0/1       203.0.113.2    administratively down   down\n"
        ),
        expected_fault="WAN-facing interface Gi0/1 is administratively shut down",
        osi_layer="Layer 1", concept_tag="interface-shutdown",
    ),
    dict(
        case_id="C008", category="Gateway", severity="Medium",
        symptom="Half the PCs on VLAN 10 can reach the gateway, the other half cannot, despite identical config.",
        topology_note="VLAN 10 spans two switches with a redundant link between them.",
        show_output=(
            "SW1# show spanning-tree vlan 10\n"
            "Interface        Role  Sts   Cost\n"
            "Gi0/1            Root  FWD   4\n"
            "Gi0/2            Altn  BLK   4\n\n"
            "SW2# show interfaces status\n"
            "Port    Status         Vlan\n"
            "Gi0/2   connected      10\n"
        ),
        expected_fault="Not a fault - STP is correctly blocking the redundant Gi0/2 path; problem is elsewhere (verify access-port VLAN membership on the affected hosts, not STP)",
        osi_layer="Layer 2", concept_tag="stp-red-herring",
    ),
    dict(
        case_id="C009", category="Gateway", severity="Low",
        symptom="PC has a valid IP and gateway but 'ping gateway' times out intermittently.",
        topology_note="Duplex settings were changed during a recent switch swap.",
        show_output=(
            "SW1# show interfaces fa0/1\n"
            "FastEthernet0/1 is up, line protocol is up\n"
            "  Full-duplex, 100Mb/s\n"
            "  5 minute input rate 0 bits/sec, 0 packets/sec\n"
            "  Total output errors: 0, collisions: 0, late collision: 4210\n"
        ),
        expected_fault="Duplex mismatch between PC NIC (likely half-duplex) and switchport (full-duplex) causing late collisions",
        osi_layer="Layer 1", concept_tag="duplex-mismatch",
    ),

    # ---------------- DHCP (4) ----------------
    dict(
        case_id="C010", category="DHCP", severity="High",
        symptom="PCs on VLAN 20 are getting 169.254.x.x addresses instead of DHCP-assigned addresses.",
        topology_note="DHCP server is a Windows server on VLAN 99, R1 provides inter-VLAN routing.",
        show_output=(
            "R1# show run interface gi0/0.20\n"
            "interface GigabitEthernet0/0.20\n"
            " encapsulation dot1Q 20\n"
            " ip address 192.168.20.1 255.255.255.0\n"
            "! no ip helper-address configured\n"
        ),
        expected_fault="Missing 'ip helper-address' on the VLAN 20 sub-interface, so DHCP broadcasts never reach the remote DHCP server",
        osi_layer="Layer 3", concept_tag="missing-dhcp-relay",
    ),
    dict(
        case_id="C011", category="DHCP", severity="Medium",
        symptom="Only the first 10 PCs on VLAN 30 get an address; the rest get none.",
        topology_note="Router-based DHCP pool serves VLAN 30 (192.168.30.0/24).",
        show_output=(
            "R1# show run | section dhcp pool VLAN30\n"
            "ip dhcp pool VLAN30\n"
            " network 192.168.30.0 255.255.255.248\n"
            " default-router 192.168.30.1\n"
        ),
        expected_fault="DHCP pool network mask is /29 (only 6 usable addresses) instead of /24, exhausting the pool almost immediately",
        osi_layer="Layer 3", concept_tag="dhcp-pool-too-small",
    ),
    dict(
        case_id="C012", category="DHCP", severity="Medium",
        symptom="A specific PC always receives the same static-looking address and cannot renew via DHCP.",
        topology_note="Excluded-address range was recently changed on the DHCP router.",
        show_output=(
            "R1# show run | include excluded-address\n"
            "ip dhcp excluded-address 192.168.40.1 192.168.40.50\n\n"
            "PC-B> ipconfig\n"
            "IP Address: 192.168.40.20\n"
        ),
        expected_fault="PC-B's address (192.168.40.20) falls inside the excluded-address range, so DHCP can never legitimately lease it and the address was statically set or stale",
        osi_layer="Layer 3", concept_tag="dhcp-excluded-range",
    ),
    dict(
        case_id="C013", category="DHCP", severity="Low",
        symptom="New laptop on VLAN 10 gets no IP at all, wired desktop next to it works fine.",
        topology_note="Laptop connects through an unmanaged switch plugged into Fa0/9.",
        show_output=(
            "SW1# show interfaces fa0/9\n"
            "FastEthernet0/9 is up, line protocol is up (err-disabled)\n"
            "%PM-4-ERR_DISABLE: portfast-bpduguard error detected on Fa0/9\n"
        ),
        expected_fault="Port err-disabled by BPDU Guard because the unmanaged switch created a loop/sent a BPDU",
        osi_layer="Layer 2", concept_tag="err-disabled-bpduguard",
    ),

    # ---------------- DNS (4) ----------------
    dict(
        case_id="C014", category="DNS", severity="Medium",
        symptom="PC can ping 8.8.8.8 successfully but 'ping www.netsage.local' fails with 'Unknown host'.",
        topology_note="Internal DNS server is 192.168.99.10.",
        show_output=(
            "PC-A> ipconfig /all\n"
            "IP Address: 192.168.10.25\n"
            "Default Gateway: 192.168.10.1\n"
            "DNS Servers: 192.168.10.1\n"
        ),
        expected_fault="PC is pointed at the gateway (192.168.10.1) for DNS instead of the actual DNS server (192.168.99.10); no DNS relay configured on the router",
        osi_layer="Layer 7", concept_tag="wrong-dns-server",
    ),
    dict(
        case_id="C015", category="DNS", severity="Low",
        symptom="Name resolution works for internal names but external domains fail.",
        topology_note="Internal DNS server forwards external queries upstream.",
        show_output=(
            "DNS-Server# show run | include forwarder\n"
            "! no forwarders configured\n"
        ),
        expected_fault="Internal DNS server has no forwarder configured for external/root queries",
        osi_layer="Layer 7", concept_tag="dns-no-forwarder",
    ),
    dict(
        case_id="C016", category="DNS", severity="Medium",
        symptom="Two different PCs resolve www.netsage.local to two different IP addresses.",
        topology_note="Static DNS entries were added manually to save time.",
        show_output=(
            "DNS-Server# show host www.netsage.local\n"
            "www.netsage.local  A  192.168.50.10\n"
            "www.netsage.local  A  192.168.50.99\n"
        ),
        expected_fault="Duplicate/conflicting A records for the same hostname on the DNS server",
        osi_layer="Layer 7", concept_tag="duplicate-dns-record",
    ),
    dict(
        case_id="C017", category="DNS", severity="High",
        symptom="DNS resolution for every domain fails from every VLAN at once.",
        topology_note="DNS server sits on VLAN 99; ACL was recently applied on R1 for hardening.",
        show_output=(
            "R1# show access-lists 101\n"
            "Extended IP access list 101\n"
            " 10 deny udp any any eq 53\n"
            " 20 permit ip any any\n"
        ),
        expected_fault="ACL 101 explicitly denies UDP/53 (DNS) before the permit-any line, blocking all DNS traffic",
        osi_layer="Layer 4", concept_tag="acl-blocks-dns",
    ),

    # ---------------- Routing (5) ----------------
    dict(
        case_id="C018", category="Routing", severity="High",
        symptom="PC on VLAN 10 (192.168.10.0/24) cannot reach server on VLAN 30 (192.168.30.0/24); gateway ping works.",
        topology_note="R1 has interfaces for VLAN 10 and VLAN 30 both up.",
        show_output=(
            "R1# show ip route\n"
            "C  192.168.10.0/24 is directly connected, GigabitEthernet0/0.10\n"
            "! 192.168.30.0/24 route missing\n"
        ),
        expected_fault="No route to 192.168.30.0/24 (sub-interface down or routing not enabled between the VLANs)",
        osi_layer="Layer 3", concept_tag="missing-route",
    ),
    dict(
        case_id="C019", category="Routing", severity="High",
        symptom="Branch office (R2) cannot reach HQ subnet 10.10.0.0/16 across a point-to-point link.",
        topology_note="R1 (HQ) and R2 (Branch) run static routes over a serial link.",
        show_output=(
            "R2# show run | include ip route\n"
            "ip route 10.10.0.0 255.255.0.0 192.168.100.2\n\n"
            "R2# show ip interface brief\n"
            "Interface   IP-Address      Status  Protocol\n"
            "Serial0/0/0 192.168.100.1   up      up\n"
        ),
        expected_fault="Static route next-hop 192.168.100.2 does not exist on the link (R1's serial IP is different / typo in next-hop)",
        osi_layer="Layer 3", concept_tag="bad-static-route-next-hop",
    ),
    dict(
        case_id="C020", category="Routing", severity="Medium",
        symptom="OSPF neighbors between R1 and R2 never form (stuck in EXSTART/DOWN).",
        topology_note="Both routers configured for OSPF area 0 on the shared link.",
        show_output=(
            "R1# show ip ospf interface gi0/1\n"
            "  Process ID 1, Area 0\n"
            "  MTU 1500\n\n"
            "R2# show ip ospf interface gi0/1\n"
            "  Process ID 1, Area 0\n"
            "  MTU 1400\n"
        ),
        expected_fault="MTU mismatch between R1 (1500) and R2 (1400) on the shared OSPF link, blocking DBD exchange",
        osi_layer="Layer 3", concept_tag="ospf-mtu-mismatch",
    ),
    dict(
        case_id="C021", category="Routing", severity="Medium",
        symptom="Return traffic from server never reaches PC even though the request clearly arrives at the server.",
        topology_note="Server subnet has two possible exit routers, one is preferred.",
        show_output=(
            "SRV-R# show ip route 192.168.10.0\n"
            "S  192.168.10.0/24 [1/0] via 192.168.200.9\n"
            "! 192.168.200.9 is unreachable/not directly connected\n"
        ),
        expected_fault="Asymmetric routing - the static return route points to a next hop that is not directly reachable",
        osi_layer="Layer 3", concept_tag="asymmetric-routing",
    ),
    dict(
        case_id="C022", category="Routing", severity="Low",
        symptom="A newly added subnet 192.168.60.0/24 is reachable from R1 but not advertised to R2.",
        topology_note="R1 and R2 run RIPv2.",
        show_output=(
            "R1# show run | section router rip\n"
            "router rip\n"
            " version 2\n"
            " network 192.168.10.0\n"
            " network 192.168.30.0\n"
            "! network 192.168.60.0 not included\n"
        ),
        expected_fault="192.168.60.0/24 was never added under the RIP 'network' statements, so R1 never advertises it",
        osi_layer="Layer 3", concept_tag="rip-missing-network-statement",
    ),

    # ---------------- ACL (4) ----------------
    dict(
        case_id="C023", category="ACL", severity="High",
        symptom="PC on VLAN 10 cannot reach the file server on VLAN 30 by IP, though routing looks correct.",
        topology_note="ACL 110 applied inbound on R1 Gi0/0.30 for VLAN 30 hardening.",
        show_output=(
            "R1# show access-lists 110\n"
            "Extended IP access list 110\n"
            " 10 deny ip 192.168.10.0 0.0.0.255 any\n"
            " 20 permit ip any any\n\n"
            "R1# show ip interface gi0/0.30\n"
            "  Inbound access list is 110\n"
        ),
        expected_fault="ACL 110 explicitly denies the whole 192.168.10.0/24 subnet before the permit-any statement",
        osi_layer="Layer 3/4", concept_tag="acl-explicit-deny",
    ),
    dict(
        case_id="C024", category="ACL", severity="Medium",
        symptom="Telnet works to R1 but SSH does not, from the same management PC.",
        topology_note="VTY lines configured to accept both protocols with an access-class applied.",
        show_output=(
            "R1# show run | section line vty\n"
            "line vty 0 4\n"
            " transport input telnet\n"
            " access-class 5 in\n"
        ),
        expected_fault="'transport input telnet' only allows Telnet; SSH is not permitted on the VTY lines",
        osi_layer="Layer 7", concept_tag="vty-transport-input",
    ),
    dict(
        case_id="C025", category="ACL", severity="Medium",
        symptom="Standard ACL meant to restrict Telnet access is instead blocking all traffic from the subnet.",
        topology_note="Standard ACL 10 applied on an interface instead of on the VTY lines.",
        show_output=(
            "R1# show run | section interface Gi0/0\n"
            "interface GigabitEthernet0/0\n"
            " ip access-group 10 in\n\n"
            "R1# show access-lists 10\n"
            "Standard IP access list 10\n"
            " 10 deny 192.168.10.5\n"
            " 20 permit any\n"
        ),
        expected_fault="Standard ACL filters by source IP only and was applied on the data interface instead of the VTY lines, so it blocks 192.168.10.5's traffic entirely, not just Telnet",
        osi_layer="Layer 3", concept_tag="acl-wrong-application-point",
    ),
    dict(
        case_id="C026", category="ACL", severity="Low",
        symptom="A named ACL intended to permit only HTTP/HTTPS from the guest VLAN appears to allow everything.",
        topology_note="ACL was written but never applied to an interface.",
        show_output=(
            "R1# show ip interface gi0/0.50\n"
            "  Inbound access list is not set\n"
            "  Outbound access list is not set\n\n"
            "R1# show access-lists GUEST-WEB-ONLY\n"
            "Extended IP access list GUEST-WEB-ONLY\n"
            " 10 permit tcp any any eq 80\n"
            " 20 permit tcp any any eq 443\n"
        ),
        expected_fault="ACL GUEST-WEB-ONLY exists but is not applied to any interface, so it has no effect",
        osi_layer="Layer 3/4", concept_tag="acl-not-applied",
    ),

    # ---------------- NAT (3) ----------------
    dict(
        case_id="C027", category="NAT", severity="High",
        symptom="Internal PCs cannot reach the internet even though the default route to the ISP is present.",
        topology_note="R1 should perform PAT (NAT overload) toward the ISP interface.",
        show_output=(
            "R1# show run | section ip nat\n"
            "ip nat inside source list 1 interface Gi0/1 overload\n"
            "interface GigabitEthernet0/0\n"
            " ! ip nat inside missing\n"
            "interface GigabitEthernet0/1\n"
            " ip nat outside\n"
        ),
        expected_fault="'ip nat inside' was never applied on the LAN interface Gi0/0, so NAT never triggers for internal hosts",
        osi_layer="Layer 3", concept_tag="nat-inside-missing",
    ),
    dict(
        case_id="C028", category="NAT", severity="Medium",
        symptom="Internet access works for VLAN 10 but not for the newly added VLAN 40.",
        topology_note="NAT uses an access-list to define which inside sources are translated.",
        show_output=(
            "R1# show access-lists 1\n"
            "Standard IP access list 1\n"
            " 10 permit 192.168.10.0 0.0.0.255\n"
            "! 192.168.40.0/24 not included\n"
        ),
        expected_fault="NAT source ACL 1 does not include the VLAN 40 subnet (192.168.40.0/24), so it is never translated",
        osi_layer="Layer 3", concept_tag="nat-acl-incomplete",
    ),
    dict(
        case_id="C029", category="NAT", severity="Medium",
        symptom="Port-forwarded internal web server is unreachable from outside despite correct static NAT line.",
        topology_note="Static NAT maps 203.0.113.10:80 to 192.168.10.50:80.",
        show_output=(
            "R1# show run | include ip nat inside source static\n"
            "ip nat inside source static tcp 192.168.10.50 80 203.0.113.10 80\n\n"
            "R1# show access-lists 101\n"
            "Extended IP access list 101\n"
            " 10 deny tcp any any eq 80\n"
            " 20 permit ip any any\n"
        ),
        expected_fault="Inbound ACL 101 on the outside interface denies TCP/80 before the static NAT translation can take effect",
        osi_layer="Layer 4", concept_tag="acl-blocks-static-nat",
    ),

    # ---------------- Wireless (3) ----------------
    dict(
        case_id="C030", category="Wireless", severity="Medium",
        symptom="Laptops on the Guest Wi-Fi SSID can reach the internet but can also reach internal file servers.",
        topology_note="Guest SSID mapped to VLAN 50; isolation ACL should restrict VLAN 50 from internal subnets.",
        show_output=(
            "R1# show ip interface gi0/0.50\n"
            "  Inbound access list is not set\n\n"
            "AP1# show run | include ssid\n"
            "ssid Guest-WiFi\n"
            " vlan 50\n"
        ),
        expected_fault="No isolation ACL applied on the Guest VLAN 50 sub-interface, so guest traffic is not restricted from internal subnets",
        osi_layer="Layer 3", concept_tag="missing-guest-isolation-acl",
    ),
    dict(
        case_id="C031", category="Wireless", severity="Low",
        symptom="Some laptops connect to the corporate SSID and get an IP, others see the SSID but fail authentication.",
        topology_note="WPA2-Enterprise with RADIUS authentication.",
        show_output=(
            "AP1# show run | include radius\n"
            "radius-server host 192.168.99.20 key CorpKey123\n\n"
            "RADIUS-Server# show log | include auth\n"
            "AUTH FAIL: shared secret mismatch from 192.168.1.5\n"
        ),
        expected_fault="RADIUS shared-secret mismatch between the AP/WLC config and the RADIUS server for some clients/policies",
        osi_layer="Layer 2", concept_tag="radius-shared-secret-mismatch",
    ),
    dict(
        case_id="C032", category="Wireless", severity="Medium",
        symptom="Wi-Fi clients near the edge of the building frequently disconnect and reconnect.",
        topology_note="Two APs with overlapping coverage were installed on the same channel.",
        show_output=(
            "AP1# show controllers dot11radio 0 | include Channel\n"
            "Channel: 6\n\n"
            "AP2# show controllers dot11radio 0 | include Channel\n"
            "Channel: 6\n"
        ),
        expected_fault="Co-channel interference: AP1 and AP2 are configured on the same channel (6) in overlapping coverage areas",
        osi_layer="Layer 1", concept_tag="wifi-channel-overlap",
    ),
]

FIELDS = [
    "case_id", "category", "severity", "symptom", "topology_note",
    "show_output", "expected_fault", "osi_layer", "concept_tag",
]

def main():
    out_path = os.path.join(os.path.dirname(__file__), "..", "data", "cases.csv")
    out_path = os.path.abspath(out_path)
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for c in CASES:
            writer.writerow(c)
    print(f"Wrote {len(CASES)} cases to {out_path}")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Ryu Application for Collecting SDN Statistics
Collects flow and port statistics from switches and writes to CSV
"""

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, set_ev_cls
from ryu.lib import hub
from ryu.ofproto import ofproto_v1_3
import csv
import time
import os
from datetime import datetime
from collections import defaultdict

class StatsCollector(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    
    def __init__(self, *args, **kwargs):
        super(StatsCollector, self).__init__(*args, **kwargs)
        self.datapaths = {}
        self.port_stats = defaultdict(dict)
        self.flow_stats = defaultdict(dict)
        self.link_stats = defaultdict(dict)
        self.poll_interval = 10  # seconds
        self.data_dir = 'data/raw'
        
        # Create data directory if it doesn't exist
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Initialize CSV file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.csv_file = os.path.join(self.data_dir, f'traffic_{timestamp}.csv')
        self._init_csv()
        
        # Start polling thread
        self.poll_thread = hub.spawn(self._poll_stats)
        
    def _init_csv(self):
        """Initialize CSV file with headers"""
        headers = [
            'time', 'link_id', 'src_switch', 'dst_switch', 'in_port', 'out_port',
            'tx_packets', 'rx_packets', 'tx_bytes', 'rx_bytes',
            'tx_bitrate', 'rx_bitrate', 'packet_loss', 'latency_ms',
            'throughput_kbps', 'tx_avg_packet_size', 'rx_avg_packet_size'
        ]
        
        with open(self.csv_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
    
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, MAIN_DISPATCHER)
    def switch_features_handler(self, ev):
        """Handle switch connection"""
        datapath = ev.msg.datapath
        if datapath.id not in self.datapaths:
            self.datapaths[datapath.id] = datapath
            self.logger.info(f'Switch connected: dpid={datapath.id}')
            self._request_stats(datapath)
    
    @set_ev_cls(ofp_event.EventOFPStateChange, MAIN_DISPATCHER)
    def state_change_handler(self, ev):
        """Handle switch disconnection"""
        datapath = ev.datapath
        if ev.state == MAIN_DISPATCHER:
            if datapath.id in self.datapaths:
                del self.datapaths[datapath.id]
                self.logger.info(f'Switch disconnected: dpid={datapath.id}')
    
    def _request_stats(self, datapath):
        """Request statistics from switch"""
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        
        # Request port stats
        req = parser.OFPPortStatsRequest(datapath, 0, ofproto.OFPP_ANY)
        datapath.send_msg(req)
        
        # Request flow stats
        req = parser.OFPFlowStatsRequest(datapath)
        datapath.send_msg(req)
    
    @set_ev_cls(ofp_event.EventOFPPortStatsReply, MAIN_DISPATCHER)
    def port_stats_reply_handler(self, ev):
        """Handle port statistics reply"""
        body = ev.msg.body
        dpid = ev.msg.datapath.id
        
        for stat in body:
            port_no = stat.port_no
            if port_no == ev.msg.datapath.ofproto.OFPP_LOCAL:
                continue
            
            # Store port statistics
            self.port_stats[dpid][port_no] = {
                'rx_packets': stat.rx_packets,
                'tx_packets': stat.tx_packets,
                'rx_bytes': stat.rx_bytes,
                'tx_bytes': stat.tx_bytes,
                'rx_errors': stat.rx_errors,
                'tx_errors': stat.tx_errors,
                'rx_dropped': stat.rx_dropped,
                'tx_dropped': stat.tx_dropped,
            }
    
    @set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
    def flow_stats_reply_handler(self, ev):
        """Handle flow statistics reply"""
        body = ev.msg.body
        dpid = ev.msg.datapath.id
        
        for stat in body:
            # Store flow statistics
            match = stat.match
            in_port = match.get('in_port', 0)
            
            self.flow_stats[dpid][in_port] = {
                'packet_count': stat.packet_count,
                'byte_count': stat.byte_count,
                'duration_sec': stat.duration_sec,
                'duration_nsec': stat.duration_nsec,
            }
    
    def _poll_stats(self):
        """Poll statistics periodically and write to CSV"""
        while True:
            hub.sleep(self.poll_interval)
            
            if not self.datapaths:
                continue
            
            timestamp = datetime.now().isoformat()
            current_time = time.time()
            
            # Collect and write statistics
            rows = []
            
            for dpid, datapath in self.datapaths.items():
                # Request fresh stats
                self._request_stats(datapath)
                
                # Process port stats
                for port_no, stats in self.port_stats[dpid].items():
                    # Calculate derived metrics
                    tx_bytes = stats['tx_bytes']
                    rx_bytes = stats['rx_bytes']
                    tx_packets = stats['tx_packets']
                    rx_packets = stats['rx_packets']
                    
                    # Calculate bitrates (bytes per second, converted to kbps)
                    # Note: This is a simplified calculation
                    tx_bitrate = (tx_bytes * 8) / (self.poll_interval * 1000)  # kbps
                    rx_bitrate = (rx_bytes * 8) / (self.poll_interval * 1000)  # kbps
                    
                    # Calculate average packet sizes
                    tx_avg_packet_size = tx_bytes / tx_packets if tx_packets > 0 else 0
                    rx_avg_packet_size = rx_bytes / rx_packets if rx_packets > 0 else 0
                    
                    # Calculate packet loss (simplified)
                    packet_loss = stats['rx_dropped'] + stats['tx_dropped']
                    
                    # Estimate latency (simplified - would need RTT measurements in real scenario)
                    latency_ms = 1.0  # Placeholder
                    
                    # Calculate throughput
                    throughput_kbps = max(tx_bitrate, rx_bitrate)
                    
                    # Create link identifier
                    link_id = f's{dpid}_p{port_no}'
                    
                    row = [
                        timestamp,
                        link_id,
                        f'switch_{dpid}',
                        'unknown',  # Would need topology info for actual dst
                        port_no,
                        port_no,  # Simplified
                        tx_packets,
                        rx_packets,
                        tx_bytes,
                        rx_bytes,
                        tx_bitrate,
                        rx_bitrate,
                        packet_loss,
                        latency_ms,
                        throughput_kbps,
                        tx_avg_packet_size,
                        rx_avg_packet_size
                    ]
                    rows.append(row)
            
            # Write rows to CSV
            if rows:
                with open(self.csv_file, 'a', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerows(rows)
                
                self.logger.info(f'Written {len(rows)} statistics records to {self.csv_file}')


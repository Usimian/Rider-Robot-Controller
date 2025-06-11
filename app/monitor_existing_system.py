#!/usr/bin/env python3
# coding=utf-8

# Monitor Existing Robot System
# This script monitors the running robot controller for errors without interfering
# Marc Wester

import sys
import time
import subprocess
import json
import signal
from datetime import datetime, timedelta

class SystemMonitor:
    def __init__(self, duration_minutes=60):
        self.duration_minutes = duration_minutes
        self.running = False
        self.start_time = None
        
        # Statistics
        self.stats = {
            'start_time': None,
            'checks_performed': 0,
            'robot_controller_restarts': 0,
            'high_cpu_events': 0,
            'high_memory_events': 0,
            'mqtt_connections': [],
            'system_errors': []
        }
        
        # Thresholds
        self.cpu_threshold = 80.0
        self.memory_threshold = 85.0
        self.check_interval = 10.0  # Check every 10 seconds
        self.report_interval = 120.0  # Report every 2 minutes
        
        # Last check times
        self.last_check = 0
        self.last_report = 0
        
        # Initial robot controller PID
        self.initial_robot_pid = None
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        print(f"\n⏹️  Received signal {signum}, stopping monitor...")
        self.running = False
    
    def log_event(self, category, message):
        """Log an event with timestamp"""
        event = {
            'timestamp': datetime.now().isoformat(),
            'category': category,
            'message': message
        }
        self.stats['system_errors'].append(event)
        print(f"⚠️  {datetime.now().strftime('%H:%M:%S')} {category}: {message}")
    
    def log_info(self, message):
        """Log informational message"""
        print(f"ℹ️  {datetime.now().strftime('%H:%M:%S')} {message}")
    
    def get_robot_controller_status(self):
        """Check robot controller process status"""
        try:
            result = subprocess.run(['pgrep', '-f', 'rider_controller'], 
                                  capture_output=True, text=True)
            
            if result.stdout.strip():
                pids = result.stdout.strip().split('\n')
                current_pid = int(pids[0]) if pids[0] else None
                
                # Check if PID changed (restart detected)
                if self.initial_robot_pid is None:
                    self.initial_robot_pid = current_pid
                    self.log_info(f"Robot controller found: PID {current_pid}")
                elif current_pid != self.initial_robot_pid:
                    self.stats['robot_controller_restarts'] += 1
                    self.log_event("RESTART", f"Robot controller restarted: {self.initial_robot_pid} -> {current_pid}")
                    self.initial_robot_pid = current_pid
                
                return {
                    'running': True,
                    'pid': current_pid,
                    'pids': pids
                }
            else:
                if self.initial_robot_pid is not None:
                    self.log_event("STOPPED", "Robot controller stopped")
                    self.initial_robot_pid = None
                
                return {
                    'running': False,
                    'pid': None,
                    'pids': []
                }
                
        except Exception as e:
            self.log_event("CHECK_ERROR", f"Failed to check robot controller: {e}")
            return {'running': False, 'pid': None, 'pids': []}
    
    def check_mqtt_connections(self):
        """Check MQTT connections"""
        try:
            result = subprocess.run(['netstat', '-an'], capture_output=True, text=True)
            connections = []
            
            for line in result.stdout.split('\n'):
                if ':1883' in line and 'ESTABLISHED' in line:
                    connections.append(line.strip())
            
            # Store connection count history
            self.stats['mqtt_connections'].append({
                'timestamp': datetime.now().isoformat(),
                'count': len(connections),
                'details': connections[:3]  # Store first 3 connections
            })
            
            return {
                'count': len(connections),
                'connections': connections
            }
            
        except Exception as e:
            self.log_event("MQTT_CHECK", f"Failed to check MQTT connections: {e}")
            return {'count': 0, 'connections': []}
    
    def check_system_resources(self):
        """Check system CPU and memory usage"""
        try:
            import psutil
            
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            
            # Check thresholds
            if cpu_percent > self.cpu_threshold:
                self.stats['high_cpu_events'] += 1
                self.log_event("HIGH_CPU", f"CPU usage: {cpu_percent:.1f}% (threshold: {self.cpu_threshold}%)")
            
            if memory.percent > self.memory_threshold:
                self.stats['high_memory_events'] += 1
                self.log_event("HIGH_MEMORY", f"Memory usage: {memory.percent:.1f}% (threshold: {self.memory_threshold}%)")
            
            return {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_used_mb': memory.used // 1024 // 1024
            }
            
        except Exception as e:
            self.log_event("RESOURCE_CHECK", f"Failed to check system resources: {e}")
            return {'cpu_percent': 0, 'memory_percent': 0, 'memory_used_mb': 0}
    
    def check_robot_screen_errors(self):
        """Check if robot screen is showing errors (indirect method)"""
        # This checks for patterns that might indicate screen errors
        # by looking at system messages or log patterns
        try:
            # Check for recent errors in dmesg
            result = subprocess.run(['dmesg', '--since', '1 hour ago'], 
                                  capture_output=True, text=True)
            
            error_patterns = ['error', 'failed', 'timeout', 'conflict']
            recent_errors = []
            
            for line in result.stdout.lower().split('\n'):
                if any(pattern in line for pattern in error_patterns):
                    if 'serial' in line or 'tty' in line or 'bluetooth' in line:
                        recent_errors.append(line.strip())
            
            return recent_errors[-5:]  # Return last 5 relevant errors
            
        except Exception as e:
            return []
    
    def generate_status_report(self):
        """Generate periodic status report"""
        if not self.start_time:
            return
            
        now = datetime.now()
        elapsed = now - self.start_time
        elapsed_minutes = elapsed.total_seconds() / 60
        
        print(f"\n{'='*70}")
        print(f"📊 SYSTEM MONITORING REPORT")
        print(f"{'='*70}")
        print(f"⏱️  Running time: {elapsed_minutes:.1f} / {self.duration_minutes} minutes")
        print(f"📈 Progress: {(elapsed_minutes/self.duration_minutes)*100:.1f}%")
        print(f"🕒 Current time: {now.strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Robot controller status
        robot_status = self.get_robot_controller_status()
        print(f"🤖 Robot Controller:")
        if robot_status['running']:
            print(f"   Status: ✅ Running (PID: {robot_status['pid']})")
        else:
            print(f"   Status: ❌ Not running")
        print(f"   Restarts detected: {self.stats['robot_controller_restarts']}")
        print()
        
        # MQTT status
        mqtt_status = self.check_mqtt_connections()
        print(f"📡 MQTT Connections:")
        print(f"   Current connections: {mqtt_status['count']}")
        if mqtt_status['connections']:
            print(f"   Latest: {mqtt_status['connections'][0][:60]}...")
        print()
        
        # System resources
        resources = self.check_system_resources()
        print(f"💻 System Resources:")
        print(f"   CPU: {resources['cpu_percent']:.1f}%")
        print(f"   Memory: {resources['memory_percent']:.1f}% ({resources['memory_used_mb']}MB)")
        print(f"   High CPU events: {self.stats['high_cpu_events']}")
        print(f"   High memory events: {self.stats['high_memory_events']}")
        print()
        
        # Recent errors
        recent_errors = [e for e in self.stats['system_errors'] 
                        if datetime.fromisoformat(e['timestamp']) > now - timedelta(minutes=10)]
        print(f"🚨 System Issues:")
        print(f"   Total errors logged: {len(self.stats['system_errors'])}")
        print(f"   Recent errors (10 min): {len(recent_errors)}")
        
        if recent_errors:
            print(f"   Latest: {recent_errors[-1]['category']} - {recent_errors[-1]['message'][:50]}...")
        
        # Assessment
        print(f"\n🎯 Current Assessment:")
        
        assessment_score = 0
        if robot_status['running']:
            assessment_score += 40
        if self.stats['robot_controller_restarts'] == 0:
            assessment_score += 20
        if resources['cpu_percent'] < 70:
            assessment_score += 20
        if resources['memory_percent'] < 80:
            assessment_score += 20
        
        if assessment_score >= 90:
            print("✅ EXCELLENT: System is very stable")
        elif assessment_score >= 70:
            print("✅ GOOD: System is stable with minor issues")
        elif assessment_score >= 50:
            print("⚠️  ACCEPTABLE: Some stability issues present")
        else:
            print("🚨 POOR: Significant system issues detected")
        
        print(f"{'='*70}\n")
    
    def save_final_report(self):
        """Save final monitoring report"""
        self.stats['end_time'] = datetime.now().isoformat()
        self.stats['duration_minutes'] = self.duration_minutes
        
        report_file = f"system_monitor_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            with open(report_file, 'w') as f:
                json.dump(self.stats, f, indent=2)
            print(f"📄 Final monitoring report saved to: {report_file}")
        except Exception as e:
            print(f"⚠️  Failed to save report: {e}")
    
    def run_monitor(self):
        """Run the system monitoring"""
        print(f"👁️  Starting System Monitoring")
        print(f"Duration: {self.duration_minutes} minutes")
        print(f"{'='*50}")
        
        self.running = True
        self.start_time = datetime.now()
        self.stats['start_time'] = self.start_time.isoformat()
        
        print(f"✅ Monitoring started at {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📊 Checking system every {self.check_interval}s")
        print(f"📋 Status reports every {self.report_interval/60:.0f} minutes")
        print("🔍 This monitors the existing robot controller without interfering")
        print("💡 Connect your PC client anytime - the monitor will detect changes")
        print("🔍 Press Ctrl+C to stop monitoring early\n")
        
        try:
            while self.running:
                current_time = time.time()
                
                # Perform system checks
                if current_time - self.last_check >= self.check_interval:
                    self.stats['checks_performed'] += 1
                    self.get_robot_controller_status()
                    self.check_mqtt_connections()
                    self.check_system_resources()
                    self.last_check = current_time
                
                # Generate status report
                if current_time - self.last_report >= self.report_interval:
                    self.generate_status_report()
                    self.last_report = current_time
                
                # Check if monitoring duration completed
                elapsed = datetime.now() - self.start_time
                if elapsed.total_seconds() >= self.duration_minutes * 60:
                    print(f"⏰ Monitoring duration completed ({self.duration_minutes} minutes)")
                    break
                
                # Brief sleep
                time.sleep(1.0)
                
        except KeyboardInterrupt:
            print(f"\n⏹️  Monitoring stopped by user")
        
        finally:
            self.running = False
            self.generate_status_report()
            self.save_final_report()
        
        return True

def main():
    print("👁️  System Monitor for Robot Controller")
    print("=" * 50)
    
    # Get monitoring duration
    try:
        duration_input = input("Enter monitoring duration in minutes (default: 30): ").strip()
        duration = int(duration_input) if duration_input else 30
        if duration < 1:
            duration = 30
    except:
        duration = 30
    
    print(f"\n📋 Monitoring Configuration:")
    print(f"   Duration: {duration} minutes")
    print(f"   System checks every 10 seconds")
    print(f"   Status reports every 2 minutes")
    print(f"   Non-interfering monitoring mode")
    
    confirm = input(f"\n🚀 Start {duration}-minute system monitoring? (y/N): ").strip().lower()
    if confirm not in ['y', 'yes']:
        print("Monitoring cancelled.")
        return
    
    # Run the monitor
    monitor = SystemMonitor(duration_minutes=duration)
    monitor.run_monitor()
    
    print(f"\n🎯 System monitoring completed!")
    print(f"Check the generated report file for detailed results.")

if __name__ == "__main__":
    main() 
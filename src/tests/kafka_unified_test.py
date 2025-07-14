#!/usr/bin/env python3
"""
Unified Kafka Test Suite
This comprehensive test file combines all Kafka testing functionality:
1. Topic management (reset/create)
2. Connectivity testing
3. Producer testing
4. Consumer testing
5. Integration testing
"""
import asyncio
import json
import sys
import os
import subprocess
import time
import signal
from pathlib import Path
from datetime import datetime

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from aiokafka.admin import AIOKafkaAdminClient
    from src.kafka.kafka_client import get_producer, get_consumer
    from src.core.ai_logger import get_ai_logger
    from src.config import KAFKA_BOOTSTRAP_SERVER
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running this from the project root directory")
    sys.exit(1)

logger = get_ai_logger()

class KafkaUnifiedTest:
    """Comprehensive Kafka testing suite"""
    
    def __init__(self):
        self.producer = None
        self.expected_topics = [
            "GROUP_EVENT", "GROUP_GENERATE", 
            "GROUP_RECOMMEND_QUESTION", "GROUP_RECOMMEND"
        ]
        self.expected_dlq_topics = [
            "GROUP_EVENT_DLQ", "GROUP_GENERATE_DLQ",
            "GROUP_RECOMMEND_QUESTION_DLQ", "GROUP_RECOMMEND_DLQ"
        ]
    
    # ==================== TOPIC MANAGEMENT ====================
    
    def run_command(self, cmd):
        """Run a shell command and return success status"""
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"Warning: {cmd}")
                print(f"Error: {result.stderr}")
                return False
            return True
        except Exception as e:
            print(f"Exception running {cmd}: {e}")
            return False
    
    def get_topics(self):
        """Get list of current topics"""
        try:
            result = subprocess.run(
                "docker exec -it kafka-local kafka-topics.sh --bootstrap-server localhost:9092 --list",
                shell=True, capture_output=True, text=True
            )
            if result.returncode == 0:
                topics = [topic.strip() for topic in result.stdout.split('\n') if topic.strip()]
                # Filter out system topics
                topics = [t for t in topics if not t.startswith('__consumer_offsets')]
                return topics
            return []
        except Exception as e:
            print(f"Error getting topics: {e}")
            return []
    
    def reset_kafka_topics(self):
        """Delete all existing topics and create unified structure"""
        print("🧹 Resetting Kafka topics...")
        
        # Delete all existing topics
        topics = self.get_topics()
        if topics:
            print(f"📋 Deleting {len(topics)} existing topics...")
            for topic in topics:
                cmd = f"docker exec -it kafka-local kafka-topics.sh --bootstrap-server localhost:9092 --delete --topic {topic}"
                self.run_command(cmd)
        
        # Wait for deletion
        time.sleep(3)
        
        # Create new unified topics
        all_topics = self.expected_topics + self.expected_dlq_topics
        print(f"🏗️ Creating {len(all_topics)} unified topics...")
        
        for topic in all_topics:
            cmd = f"""docker exec -it kafka-local kafka-topics.sh \\
                --bootstrap-server localhost:9092 \\
                --create \\
                --topic {topic} \\
                --partitions 3 \\
                --replication-factor 1"""
            self.run_command(cmd)
        
        # Verify creation
        final_topics = set(self.get_topics())
        expected_set = set(all_topics)
        
        if expected_set.issubset(final_topics):
            print("✅ All topics created successfully")
            return True
        else:
            missing = expected_set - final_topics
            print(f"❌ Missing topics: {missing}")
            return False
    
    # ==================== CONNECTIVITY TESTING ====================
    
    async def test_kafka_connectivity(self):
        """Test basic Kafka connection and topic availability"""
        print("🔍 Testing Kafka connectivity...")
        
        admin_client = None
        try:
            admin_client = AIOKafkaAdminClient(bootstrap_servers=KAFKA_BOOTSTRAP_SERVER)
            await admin_client.start()
            print("✅ Kafka connection established")
            
            # Test topic access
            for topic in self.expected_topics:
                try:
                    metadata = await admin_client.describe_topics([topic])
                    if metadata and topic in metadata:
                        print(f"   ✅ {topic}: accessible")
                    else:
                        print(f"   ❌ {topic}: not found")
                except Exception as e:
                    print(f"   ❌ {topic}: error - {e}")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to connect to Kafka: {e}")
            return False
        finally:
            if admin_client:
                try:
                    await admin_client.close()
                except Exception:
                    pass
    
    # ==================== PRODUCER TESTING ====================
    
    async def start_producer(self):
        """Start the test producer"""
        try:
            self.producer = get_producer()
            await self.producer.start()
            logger.info("[Test Producer] Started")
            return True
        except Exception as e:
            print(f"❌ Failed to start producer: {e}")
            return False
    
    async def stop_producer(self):
        """Stop the test producer"""
        if self.producer:
            try:
                await self.producer.stop()
                logger.info("[Test Producer] Stopped")
            except Exception as e:
                print(f"⚠️ Error stopping producer: {e}")
    
    async def send_test_messages(self):
        """Send test messages to all unified topics"""
        print("📤 Sending test messages to unified topics...")
        
        # Test GROUP_EVENT messages
        print("   📧 Testing GROUP_EVENT...")
        group_events = [
            {
                "eventType": "GROUP_CREATED",
                "data": {
                    "groupId": 9999,
                    "name": "Unified Test Group",
                    "category": "Technology",
                    "summary": "Testing unified consumer architecture",
                    "description": "Integration test for unified Kafka system",
                    "plan": "1. Test consumers\n2. Verify processing\n3. Check integration",
                    "location": "Seoul, Korea",
                    "currentUserCount": 1,
                    "maxUserCount": 20,
                    "imageUrl": "test.jpg",
                    "tags": ["test", "unified", "kafka"]
                },
                "timestamp": [2025, 7, 14, 16, 0, 0, 0]
            },
            {
                "eventType": "GROUP_JOINED",
                "data": {"userId": 1001, "groupId": 9999},
                "timestamp": [2025, 7, 14, 16, 5, 0, 0]
            }
        ]
        
        for event in group_events:
            try:
                await self.producer.send_and_wait("GROUP_EVENT", event)
                print(f"      ✅ Sent: {event['eventType']}")
            except Exception as e:
                print(f"      ❌ Failed: {event['eventType']} - {e}")
        
        # Test GROUP_GENERATE
        print("   🤖 Testing GROUP_GENERATE...")
        generate_request = {
            "name": "Unified Test AI Group",
            "goal": "Test unified consumer architecture with AI",
            "category": "Technology",
            "period": "2 weeks",
            "isPlanCreated": True
        }
        try:
            await self.producer.send_and_wait("GROUP_GENERATE", generate_request)
            print("      ✅ Sent: Group generation request")
        except Exception as e:
            print(f"      ❌ Failed: Group generation - {e}")
        
        # Test GROUP_RECOMMEND_QUESTION
        print("   ❓ Testing GROUP_RECOMMEND_QUESTION...")
        question_request = {
            "type": "CREATE_QUESTION",
            "payload": {
                "sessionId": "unified-test-session",
                "userId": 1001,
                "answer": "Testing unified consumer system"
            }
        }
        try:
            await self.producer.send_and_wait("GROUP_RECOMMEND_QUESTION", question_request)
            print("      ✅ Sent: Question generation request")
        except Exception as e:
            print(f"      ❌ Failed: Question generation - {e}")
        
        # Test GROUP_RECOMMEND
        print("   💡 Testing GROUP_RECOMMEND...")
        recommend_request = {
            "type": "RECOMMEND_REQUEST",
            "payload": {
                "sessionId": "unified-test-session",
                "userId": 1001,
                "messages": [
                    {"role": "user", "text": "Test unified system"},
                    {"role": "assistant", "text": "What would you like to test?"},
                    {"role": "user", "text": "Consumer processing and integration"}
                ]
            }
        }
        try:
            await self.producer.send_and_wait("GROUP_RECOMMEND", recommend_request)
            print("      ✅ Sent: Recommendation request")
        except Exception as e:
            print(f"      ❌ Failed: Recommendation - {e}")
        
        print("✅ Test message sending completed")
    
    # ==================== CONSUMER TESTING ====================
    
    def start_ai_server(self):
        """Start the AI server with consumers"""
        print("🚀 Starting AI server...")
        try:
            process = subprocess.Popen([
                sys.executable, '-m', 'src.main'
            ], 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1,
            cwd=project_root
            )
            return process
        except Exception as e:
            print(f"❌ Failed to start AI server: {e}")
            return None
    
    def check_server_logs(self, process, duration=10):
        """Check server logs for consumer activity"""
        print(f"📊 Monitoring server logs for {duration} seconds...")
        
        consumers_started = []
        messages_processed = 0
        
        start_time = time.time()
        
        try:
            while time.time() - start_time < duration:
                if process.poll() is not None:
                    break
                    
                line = process.stdout.readline()
                if line:
                    line = line.strip()
                    print(f"[SERVER] {line}")
                    
                    # Check for consumer startup
                    if "Successfully started consumer for" in line:
                        for topic in self.expected_topics:
                            if f"'{topic}'" in line:
                                consumers_started.append(topic)
                                break
                    
                    # Check for processing activity
                    if any(keyword in line.lower() for keyword in [
                        "processing", "processed", "chromadb", "started consumer for"
                    ]):
                        messages_processed += 1
                
                time.sleep(0.1)
        
        except Exception as e:
            print(f"⚠️ Error reading logs: {e}")
        
        return consumers_started, messages_processed
    
    def stop_server(self, process):
        """Stop the AI server gracefully"""
        print("🛑 Stopping AI server...")
        try:
            process.terminate()
            try:
                process.wait(timeout=10)
                print("✅ Server stopped gracefully")
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
                print("⚠️ Server force stopped")
        except Exception as e:
            print(f"⚠️ Error stopping server: {e}")
    
    # ==================== INTEGRATION TESTING ====================
    
    async def run_integration_test(self):
        """Run complete integration test"""
        print("🧪 Running integration test...")
        
        server_process = None
        try:
            # Start server
            server_process = self.start_ai_server()
            if not server_process:
                return False
            
            # Wait for startup
            print("⏳ Waiting for server startup...")
            time.sleep(8)
            
            # Check initial logs
            consumers_started, initial_logs = self.check_server_logs(server_process, 5)
            
            # Send test messages
            if not await self.start_producer():
                return False
            
            await self.send_test_messages()
            await self.stop_producer()
            
            # Monitor processing
            print("📈 Monitoring message processing...")
            time.sleep(2)
            processing_consumers, processing_logs = self.check_server_logs(server_process, 5)
            
            # Report results
            print("\n📊 Integration Test Results:")
            print(f"   Consumers Started: {len(set(consumers_started))}/4")
            print(f"   Processing Activity: {processing_logs} log entries")
            
            success = len(set(consumers_started)) >= 4
            return success
            
        except Exception as e:
            print(f"❌ Integration test failed: {e}")
            return False
        finally:
            if server_process:
                self.stop_server(server_process)
    
    # ==================== VERIFICATION ====================
    
    def verify_topic_messages(self):
        """Verify messages are in topics"""
        print("🔍 Verifying topic messages...")
        
        for topic in self.expected_topics:
            try:
                result = subprocess.run([
                    "docker", "exec", "-it", "kafka-local", 
                    "kafka-run-class.sh", "kafka.tools.GetOffsetShell",
                    "--broker-list", "localhost:9092",
                    "--topic", topic,
                    "--time", "-1"
                ], capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0 and result.stdout.strip():
                    lines = result.stdout.strip().split('\n')
                    total_messages = sum(int(line.split(':')[-1]) for line in lines if ':' in line)
                    print(f"   ✅ {topic}: {total_messages} messages")
                else:
                    print(f"   ⚠️ {topic}: no messages or error")
            except Exception as e:
                print(f"   ❌ {topic}: error checking - {e}")
    
    # ==================== MAIN TEST RUNNER ====================
    
    async def run_all_tests(self, include_reset=False):
        """Run all tests in sequence"""
        print("=" * 80)
        print("🧪 UNIFIED KAFKA TEST SUITE")
        print("=" * 80)
        
        # Prerequisites
        print("📋 Checking prerequisites...")
        if not os.path.exists(project_root / "src" / "main.py"):
            print("❌ Error: Cannot find src/main.py")
            return False
        
        try:
            result = subprocess.run([
                "docker", "exec", "kafka-local", "kafka-topics.sh", 
                "--bootstrap-server", "localhost:9092", "--list"
            ], capture_output=True, timeout=5)
            if result.returncode != 0:
                print("❌ Kafka is not accessible")
                return False
        except Exception:
            print("❌ Cannot access Kafka")
            return False
        
        print("✅ Prerequisites OK")
        
        # Test sequence
        all_passed = True
        
        # 1. Topic Reset (optional)
        if include_reset:
            print(f"\n{'='*20} TOPIC RESET {'='*20}")
            if not self.reset_kafka_topics():
                print("❌ Topic reset failed")
                all_passed = False
        
        # 2. Connectivity Test
        print(f"\n{'='*20} CONNECTIVITY TEST {'='*20}")
        if not await self.test_kafka_connectivity():
            print("❌ Connectivity test failed")
            all_passed = False
        
        # 3. Producer Test
        print(f"\n{'='*20} PRODUCER TEST {'='*20}")
        if await self.start_producer():
            await self.send_test_messages()
            await self.stop_producer()
            print("✅ Producer test completed")
        else:
            print("❌ Producer test failed")
            all_passed = False
        
        # 4. Message Verification
        print(f"\n{'='*20} MESSAGE VERIFICATION {'='*20}")
        self.verify_topic_messages()
        
        # 5. Integration Test
        print(f"\n{'='*20} INTEGRATION TEST {'='*20}")
        if not await self.run_integration_test():
            print("❌ Integration test failed")
            all_passed = False
        
        # Final Results
        print("\n" + "="*80)
        if all_passed:
            print("🎉 ALL TESTS PASSED!")
            print("✅ Your unified Kafka consumer system is working correctly")
        else:
            print("❌ SOME TESTS FAILED")
            print("⚠️ Check the logs above for issues")
        print("="*80)
        
        return all_passed

def main():
    """Main entry point with command line options"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Unified Kafka Test Suite")
    parser.add_argument("--reset", action="store_true", 
                       help="Reset Kafka topics before testing")
    parser.add_argument("--connectivity-only", action="store_true",
                       help="Run only connectivity test")
    parser.add_argument("--producer-only", action="store_true",
                       help="Run only producer test")
    parser.add_argument("--integration-only", action="store_true",
                       help="Run only integration test")
    
    args = parser.parse_args()
    
    tester = KafkaUnifiedTest()
    
    async def run_tests():
        if args.connectivity_only:
            return await tester.test_kafka_connectivity()
        elif args.producer_only:
            success = await tester.start_producer()
            if success:
                await tester.send_test_messages()
                await tester.stop_producer()
            return success
        elif args.integration_only:
            return await tester.run_integration_test()
        else:
            return await tester.run_all_tests(include_reset=args.reset)
    
    try:
        success = asyncio.run(run_tests())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n❌ Tests interrupted by user")
        sys.exit(1)

if __name__ == "__main__":
    main()

import asyncio
import json
import sys
import os
import subprocess
import time
import signal
from pathlib import Path
from datetime import datetime

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
                "docker exec -it kafka kafka-topics.sh --bootstrap-server localhost:9092 --list",
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
                cmd = f"docker exec -it kafka kafka-topics.sh --bootstrap-server localhost:9092 --delete --topic {topic}"
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
    
    # ==================== MONITORING FUNCTIONS ====================
    
    async def monitor_kafka_setup(self):
        """Monitor Kafka consumer setup (from kafka_monitor.py)"""
        print("🔍 Monitoring Kafka Consumer Setup...")
        
        admin_client = AIOKafkaAdminClient(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVER,
            request_timeout_ms=10000
        )
        
        try:
            await admin_client.start()
            
            # Check topics
            topics = ["GROUP_EVENT", "GROUP_RECOMMEND_QUESTION", "GROUP_RECOMMEND"]
            existing_topics = await admin_client.describe_topics(topics)
            
            for topic in topics:
                if topic in existing_topics:
                    topic_metadata = existing_topics[topic]
                    partition_count = len(topic_metadata.partitions)
                    print(f"✅ {topic}: {partition_count} partitions")
                else:
                    print(f"❌ {topic}: Not found")
            
            # Check consumer groups
            try:
                from src.config import KAFKA_CONSUMER_GROUP_ID
                group_metadata = await admin_client.describe_consumer_groups([KAFKA_CONSUMER_GROUP_ID])
                if KAFKA_CONSUMER_GROUP_ID in group_metadata:
                    group_info = group_metadata[KAFKA_CONSUMER_GROUP_ID]
                    print(f"✅ Consumer Group: {KAFKA_CONSUMER_GROUP_ID}")
                    print(f"   Members: {len(group_info.members)}")
                else:
                    print(f"ℹ️ Consumer group {KAFKA_CONSUMER_GROUP_ID} not active yet")
            except Exception as e:
                print(f"ℹ️ Consumer group check: {e}")
            
            return True
            
        except Exception as e:
            print(f"❌ Monitoring failed: {e}")
            return False
        finally:
            await admin_client.close()

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
        """Send comprehensive test messages to all unified topics (enhanced from kafka_producer_simulation.py)"""
        print("📤 Sending comprehensive test messages to unified topics...")
        
        # Enhanced GROUP_EVENT messages with more realistic data
        print("   📧 Testing GROUP_EVENT...")
        group_events = [
            {
                "eventType": "GROUP_CREATED",
                "data": {
                    "groupId": 5001,
                    "name": "AI Study Group",
                    "category": "Technology",
                    "summary": "Weekly AI and machine learning discussions",
                    "description": "Join us to explore the latest in AI, share projects, and learn together",
                    "plan": "Meet every Thursday 7PM at Tech Hub, discuss papers, work on projects",
                    "location": "Gangnam Tech Hub, Seoul",
                    "currentUserCount": 1,
                    "maxUserCount": 12,
                    "imageUrl": "ai-study-group.jpg",
                    "tags": ["AI", "Machine Learning", "Technology", "Study"]
                },
                "timestamp": [2025, 7, 15, 14, 0, 0, 0]
            },
            {
                "eventType": "GROUP_JOINED",
                "data": {
                    "userId": 201,
                    "groupId": 5001
                },
                "timestamp": [2025, 7, 15, 14, 5, 0, 0]
            },
            {
                "eventType": "GROUP_CREATED",
                "data": {
                    "groupId": 5002,
                    "name": "Weekend Hiking Club",
                    "category": "Outdoor",
                    "summary": "Explore beautiful hiking trails around Seoul",
                    "description": "Every weekend we discover new mountains and trails, suitable for all levels",
                    "plan": "Saturday morning hikes, difficulty varies, equipment sharing available",
                    "location": "Various mountains near Seoul",
                    "currentUserCount": 1,
                    "maxUserCount": 20,
                    "imageUrl": "hiking-club.jpg",
                    "tags": ["Hiking", "Outdoor", "Weekend", "Nature"]
                },
                "timestamp": [2025, 7, 15, 14, 15, 0, 0]
            }
        ]
        
        for event in group_events:
            try:
                await self.producer.send_and_wait("GROUP_EVENT", event)
                event_type = event["eventType"]
                if event_type == "GROUP_CREATED":
                    group_name = event["data"]["name"]
                    print(f"      ✅ Sent {event_type}: {group_name}")
                else:
                    user_id = event["data"]["userId"]
                    group_id = event["data"]["groupId"]
                    print(f"      ✅ Sent {event_type}: User {user_id} → Group {group_id}")
                await asyncio.sleep(0.5)
            except Exception as e:
                print(f"      ❌ Failed: {event['eventType']} - {e}")
        
        # Test GROUP_GENERATE
        print("   🤖 Testing GROUP_GENERATE...")
        generate_request = {
            "name": "Photography Meetup",
            "goal": "Learn and practice photography techniques together",
            "category": "Arts",
            "location": "Seoul, Korea",
            "period": "Monthly",
            "maxUserCount": 15,
            "isPlanCreated": True
        }
        try:
            await self.producer.send_and_wait("GROUP_GENERATE", generate_request)
            print("      ✅ Sent: Group generation request")
        except Exception as e:
            print(f"      ❌ Failed: Group generation - {e}")
        
        # Enhanced GROUP_RECOMMEND_QUESTION messages
        print("   ❓ Testing GROUP_RECOMMEND_QUESTION...")
        question_requests = [
            {
                "type": "CREATE_QUESTION",
                "payload": {
                    "sessionId": "test-session-001",
                    "userId": 201,
                    "answer": "I'm passionate about technology and love learning new programming languages"
                }
            },
            {
                "type": "CREATE_QUESTION", 
                "payload": {
                    "sessionId": "test-session-002",
                    "userId": 202,
                    "answer": "I enjoy outdoor activities, especially hiking and camping on weekends"
                }
            }
        ]
        
        for request in question_requests:
            try:
                await self.producer.send_and_wait("GROUP_RECOMMEND_QUESTION", request)
                session_id = request["payload"]["sessionId"]
                user_id = request["payload"]["userId"]
                print(f"      ✅ Sent question request: Session {session_id}, User {user_id}")
                await asyncio.sleep(1)
            except Exception as e:
                print(f"      ❌ Failed: Question generation - {e}")
        
        # Enhanced GROUP_RECOMMEND messages
        print("   💡 Testing GROUP_RECOMMEND...")
        recommend_requests = [
            {
                "type": "RECOMMEND_REQUEST",
                "payload": {
                    "sessionId": "test-session-001",
                    "userId": 201,
                    "messages": [
                        {
                            "role": "user", 
                            "text": "I answered that I'm passionate about technology and programming"
                        },
                        {
                            "role": "assistant",
                            "text": "What specific areas of technology interest you most?"
                        },
                        {
                            "role": "user",
                            "text": "AI, machine learning, and web development"
                        }
                    ]
                }
            },
            {
                "type": "RECOMMEND_REQUEST",
                "payload": {
                    "sessionId": "test-session-002", 
                    "userId": 202,
                    "messages": [
                        {
                            "role": "user",
                            "text": "I mentioned I enjoy hiking and outdoor activities"
                        },
                        {
                            "role": "assistant", 
                            "text": "Do you prefer group activities or solo adventures?"
                        },
                        {
                            "role": "user",
                            "text": "I love group activities, meeting new people while exploring nature"
                        }
                    ]
                }
            }
        ]
        
        for request in recommend_requests:
            try:
                await self.producer.send_and_wait("GROUP_RECOMMEND", request)
                session_id = request["payload"]["sessionId"]
                user_id = request["payload"]["userId"]
                print(f"      ✅ Sent recommendation request: Session {session_id}, User {user_id}")
                await asyncio.sleep(1)
            except Exception as e:
                print(f"      ❌ Failed: Recommendation - {e}")
        
        # Test invalid messages for DLQ functionality
        print("   💀 Testing DLQ with invalid messages...")
        invalid_messages = [
            {
                "topic": "GROUP_EVENT",
                "message": {
                    "eventType": "INVALID_EVENT_TYPE",
                    "data": {"invalidField": "This will cause validation error"},
                    "timestamp": "invalid-timestamp-format"
                }
            }
        ]
        
        for invalid_msg in invalid_messages:
            try:
                topic = invalid_msg["topic"]
                message = invalid_msg["message"]
                await self.producer.send_and_wait(topic, message)
                print(f"      ✅ Sent invalid message to {topic} (should trigger DLQ)")
                await asyncio.sleep(0.5)
            except Exception as e:
                print(f"      ❌ Failed to send invalid message: {e}")
        
        print("✅ Comprehensive test message sending completed")
    
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
    
    # ==================== CONSUMER VALIDATION ====================
    
    async def test_consumer_rebalancing(self):
        """Test consumer rebalancing (from kafka_consumer_validation.py)"""
        print("⚖️ Testing consumer rebalancing...")
        
        try:
            from src.config import KAFKA_CONSUMER_GROUP_ID
            from aiokafka import AIOKafkaConsumer
            
            consumers = []
            
            # Start first consumer
            print("👷 Starting first consumer instance...")
            consumer1 = AIOKafkaConsumer(
                "GROUP_EVENT",
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVER,
                group_id=f"{KAFKA_CONSUMER_GROUP_ID}-rebalance-test",
                auto_offset_reset="latest",
                enable_auto_commit=False,
                session_timeout_ms=10000,
                heartbeat_interval_ms=3000
            )
            await consumer1.start()
            consumers.append(consumer1)
            
            await asyncio.sleep(3)  # Wait for initial assignment
            partitions1 = consumer1.assignment()
            print(f"  📊 Consumer 1 partitions: {[p.partition for p in partitions1]}")
            
            # Start second consumer
            print("👷 Starting second consumer instance...")
            consumer2 = AIOKafkaConsumer(
                "GROUP_EVENT",
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVER,
                group_id=f"{KAFKA_CONSUMER_GROUP_ID}-rebalance-test",
                auto_offset_reset="latest",
                enable_auto_commit=False,
                session_timeout_ms=10000,
                heartbeat_interval_ms=3000
            )
            await consumer2.start()
            consumers.append(consumer2)
            
            await asyncio.sleep(5)  # Wait for rebalancing
            partitions1 = consumer1.assignment()
            partitions2 = consumer2.assignment()
            print(f"  📊 After 2nd consumer - Consumer 1: {[p.partition for p in partitions1]}")
            print(f"  📊 After 2nd consumer - Consumer 2: {[p.partition for p in partitions2]}")
            
            # Start third consumer
            print("👷 Starting third consumer instance...")
            consumer3 = AIOKafkaConsumer(
                "GROUP_EVENT",
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVER,
                group_id=f"{KAFKA_CONSUMER_GROUP_ID}-rebalance-test",
                auto_offset_reset="latest",
                enable_auto_commit=False,
                session_timeout_ms=10000,
                heartbeat_interval_ms=3000
            )
            await consumer3.start()
            consumers.append(consumer3)
            
            await asyncio.sleep(5)  # Wait for final rebalancing
            partitions1 = consumer1.assignment()
            partitions2 = consumer2.assignment()
            partitions3 = consumer3.assignment()
            
            print("📊 Final partition assignment after 3rd consumer:")
            print(f"  👷 Consumer 1: {[p.partition for p in partitions1]}")
            print(f"  👷 Consumer 2: {[p.partition for p in partitions2]}")
            print(f"  👷 Consumer 3: {[p.partition for p in partitions3]}")
            
            # Verify all partitions are assigned
            all_assigned = set()
            for consumer in consumers:
                assigned = {p.partition for p in consumer.assignment()}
                all_assigned.update(assigned)
            
            expected_partitions = {0, 1, 2}
            success = all_assigned == expected_partitions
            
            # Cleanup
            for consumer in consumers:
                try:
                    await consumer.stop()
                except Exception:
                    pass
            
            if success:
                print("✅ Consumer rebalancing: PASS - All partitions properly distributed")
                return True
            else:
                missing = expected_partitions - all_assigned
                print(f"❌ Consumer rebalancing: FAIL - Missing partitions: {missing}")
                return False
            
        except Exception as e:
            print(f"❌ Consumer rebalancing test failed: {e}")
            return False

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
        
        # 2. Connectivity and Monitoring Test
        print(f"\n{'='*20} CONNECTIVITY & MONITORING TEST {'='*20}")
        if not await self.test_kafka_connectivity():
            print("❌ Connectivity test failed")
            all_passed = False
        
        if not await self.monitor_kafka_setup():
            print("❌ Monitoring test failed")
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
        
        # 5. Consumer Rebalancing Test
        print(f"\n{'='*20} CONSUMER REBALANCING TEST {'='*20}")
        if not await self.test_consumer_rebalancing():
            print("❌ Consumer rebalancing test failed")
            all_passed = False
        
        # 6. Integration Test
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

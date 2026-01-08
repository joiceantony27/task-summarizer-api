"""Quick API test script"""
import asyncio
from httpx import AsyncClient, ASGITransport
import sys
sys.path.insert(0, '.')
from main import app

async def test_api():
    print("=" * 50)
    print("TESTING API ENDPOINTS")
    print("=" * 50)
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        # Test 1: Health check
        print("\n1. Testing Health Endpoint...")
        r = await client.get('/health')
        print(f"   Status: {r.status_code}")
        print(f"   Response: {r.json()}")
        assert r.status_code == 200, "Health check failed!"
        print("   ✓ Health check PASSED")
        
        # Test 2: Create task
        print("\n2. Testing Create Task (POST)...")
        task_data = {
            'title': 'Complete Assessment',
            'description': 'Finish the Python backend engineer take-home assessment with all requirements.',
            'priority': 'high',
            'generate_summary': False
        }
        r = await client.post('/api/v1/tasks/', json=task_data)
        print(f"   Status: {r.status_code}")
        created_task = r.json()
        print(f"   Task ID: {created_task['id']}")
        print(f"   Title: {created_task['title']}")
        assert r.status_code == 201, "Create task failed!"
        print("   ✓ Create task PASSED")
        
        task_id = created_task['id']
        
        # Test 3: Get all tasks
        print("\n3. Testing Get All Tasks (GET)...")
        r = await client.get('/api/v1/tasks/')
        print(f"   Status: {r.status_code}")
        data = r.json()
        print(f"   Total tasks: {data['total']}")
        assert r.status_code == 200, "Get tasks failed!"
        print("   ✓ Get tasks PASSED")
        
        # Test 4: Get task by ID
        print(f"\n4. Testing Get Task by ID (GET /{task_id})...")
        r = await client.get(f'/api/v1/tasks/{task_id}')
        print(f"   Status: {r.status_code}")
        assert r.status_code == 200, "Get task by ID failed!"
        print("   ✓ Get task by ID PASSED")
        
        # Test 5: Update task
        print(f"\n5. Testing Update Task (PUT /{task_id})...")
        update_data = {'status': 'in_progress', 'priority': 'critical'}
        r = await client.put(f'/api/v1/tasks/{task_id}', json=update_data)
        print(f"   Status: {r.status_code}")
        updated = r.json()
        print(f"   New Status: {updated['status']}")
        print(f"   New Priority: {updated['priority']}")
        assert r.status_code == 200, "Update task failed!"
        print("   ✓ Update task PASSED")
        
        # Test 6: Delete task
        print(f"\n6. Testing Delete Task (DELETE /{task_id})...")
        r = await client.delete(f'/api/v1/tasks/{task_id}')
        print(f"   Status: {r.status_code}")
        assert r.status_code == 200, "Delete task failed!"
        print("   ✓ Delete task PASSED")
        
        # Test 7: Verify deletion (should be 404)
        print(f"\n7. Testing Get Deleted Task (should be 404)...")
        r = await client.get(f'/api/v1/tasks/{task_id}')
        print(f"   Status: {r.status_code}")
        assert r.status_code == 404, "Deleted task should not be found!"
        print("   ✓ Task correctly deleted PASSED")
        
    print("\n" + "=" * 50)
    print("ALL TESTS PASSED! ✓")
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(test_api())

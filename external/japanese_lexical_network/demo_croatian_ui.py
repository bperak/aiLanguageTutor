"""
Croatian UI Integration Demo

This script tests the new Croatian UI integration functionality
by starting the Flask app and providing test instructions.
"""

import subprocess
import time
import requests
import os
import sys

def test_croatian_ui_integration():
    """Test the Croatian UI integration."""
    print("🔧 Croatian UI Integration Demo")
    print("=" * 50)
    
    # Check if virtual environment is activated
    venv_path = os.path.join(os.getcwd(), 'venv', 'Scripts', 'python.exe')
    if not os.path.exists(venv_path):
        print("❌ Virtual environment not found!")
        print("Please run: python -m venv venv")
        return False
    
    print("✅ Virtual environment found")
    
    # Start the Flask app
    print("\n🚀 Starting Flask application...")
    print("The app should be available at: http://localhost:5000")
    print("\n📋 Testing Instructions:")
    print("1. Open http://localhost:5000 in your browser")
    print("2. You should see a language selector with 🇯🇵 Japanese and 🇭🇷 Croatian options")
    print("3. Select Croatian from the language dropdown")
    print("4. The search attributes should change to Croatian options:")
    print("   - Natuknica, Normalized, Definition, POS, UPOS, Translation")
    print("5. The search placeholder should change to 'Search for a Croatian node...'")
    print("6. Try searching for a Croatian word like 'ljubav' using 'Natuknica' attribute")
    print("7. Click on a Croatian node to see Croatian-specific information")
    print("8. Try the Croatian exercises in the 'Lexical Exercises' tab")
    print("\n🎯 Features to Test:")
    print("- Language switching functionality")
    print("- Croatian search attributes")
    print("- Croatian node information display")
    print("- Croatian exercise generation")
    print("- Multi-language graph data fetching")
    
    print("\n🖥️  Starting Flask server...")
    print("Press Ctrl+C to stop the server when done testing")
    
    # Run the Flask app
    try:
        # Use the virtual environment's Python
        result = subprocess.run([
            venv_path, 'app.py'
        ], cwd=os.getcwd())
    except KeyboardInterrupt:
        print("\n\n✅ Flask server stopped")
    except Exception as e:
        print(f"\n❌ Error starting Flask server: {e}")
        return False
    
    return True

def check_endpoints():
    """Check if Croatian endpoints are working."""
    print("\n🔍 Checking Croatian endpoints...")
    
    # Wait a moment for server to start
    time.sleep(2)
    
    endpoints_to_test = [
        '/graph-data?term=ljubav&attribute=natuknica&language=croatian',
        '/generate-croatian-exercise?node_id=ljubav-NOUN&level=2&mode=exercise',
        '/croatian-node-info?node_id=ljubav-NOUN'
    ]
    
    for endpoint in endpoints_to_test:
        try:
            response = requests.get(f'http://localhost:5000{endpoint}', timeout=10)
            if response.status_code == 200:
                print(f"✅ {endpoint} - Working")
            else:
                print(f"⚠️  {endpoint} - Status: {response.status_code}")
        except requests.RequestException as e:
            print(f"❌ {endpoint} - Error: {e}")

if __name__ == "__main__":
    print("Starting Croatian UI Integration Demo...")
    
    # Check if we're in the right directory
    if not os.path.exists('app.py'):
        print("❌ app.py not found! Please run this script from the project root directory.")
        sys.exit(1)
    
    # Run the demo
    success = test_croatian_ui_integration()
    
    if success:
        print("\n🎉 Demo completed successfully!")
        print("\nNext steps:")
        print("- Test all Croatian language features in the browser")
        print("- Verify search functionality works for both languages")
        print("- Ensure Croatian exercises generate properly")
        print("- Check that node information displays correctly for Croatian")
    else:
        print("\n❌ Demo encountered issues. Please check the logs above.") 
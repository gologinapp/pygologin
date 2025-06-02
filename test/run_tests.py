import os
import time
import sys
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from gologin import GoLogin

token = os.environ.get('GL_API_TOKEN')
profile_id = os.environ.get('GL_PROFILE_ID')

if not token:
    print('GL_API_TOKEN environment variable is required')
    sys.exit(1)

def run_test(test_name, test_function):
    """Run a test function and measure its execution time."""
    print(f'\n🧪 Running test: {test_name}')
    start_time = time.time()
    
    try:
        result = test_function()
        duration = int((time.time() - start_time) * 1000)  # Convert to milliseconds
        print(f'✅ {test_name} passed ({duration}ms)')
        
        return {
            'name': test_name,
            'status': 'passed',
            'duration': duration,
            'result': result
        }
    except Exception as error:
        duration = int((time.time() - start_time) * 1000)  # Convert to milliseconds
        print(f'❌ {test_name} failed ({duration}ms): {str(error)}')
        
        return {
            'name': test_name,
            'status': 'failed',
            'duration': duration,
            'error': str(error)
        }

def test_ip_check():
    gologin = GoLogin({
        'token': token,
        'extra_params': ['--headless', '--no-sandbox'],
        'profile_id': profile_id
    })
    print(f'gologin: {gologin}')
    try:
        debugger_address = gologin.start()
        service = Service(ChromeDriverManager(driver_version=gologin.get_chromium_version()).install())
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_experimental_option("debuggerAddress", debugger_address)
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        try:
            # Navigate to the IP check website
            driver.get('https://iphey.com/')
            
            # Wait for the page to load completely
            wait = WebDriverWait(driver, 30)
            element = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '.trustworthy:not(.hide)'))
            )
            
            # Get the status text
            status = element.text.strip()
            
            if not status:
                raise Exception('Could not get IP check status')
            
            return f'IP check status: {status}'
            
        finally:
            driver.quit()
    except Exception as e:
        print(f'❌ Test execution failed: {str(e)}')
        sys.exit(1) 

def main():
    """Main function to run all tests."""
    print('🚀 Starting E2E tests...')
    
    tests = [
        ('IP Check Test', test_ip_check),
    ]
    
    results = []
    
    for name, test_fn in tests:
        result = run_test(name, test_fn)
        results.append(result)
    
    # Print summary
    print('\n📊 Test Summary:')
    passed = len([r for r in results if r['status'] == 'passed'])
    failed = len([r for r in results if r['status'] == 'failed'])
    print(f'Total: {len(results)}, Passed: {passed}, Failed: {failed}')
    
    return results

if __name__ == '__main__':
    try:
        results = main()
        # Exit with error code if any tests failed
        failed_tests = [r for r in results if r['status'] == 'failed']
        sys.exit(len(failed_tests))
    except Exception as e:
        print(f'❌ Test execution failed: {str(e)}')
        sys.exit(1) 
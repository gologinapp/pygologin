#!/usr/bin/env python3

import os
import sys
import time
import multiprocessing
from gologin.browserManager.browserManager import BrowserManager

def test_download(major_version, process_id):
    print(f"Process {process_id}: Starting download test for version {major_version}")
    try:
        browser_manager = BrowserManager()
        executable_path = browser_manager.get_orbita_path(major_version)
        print(f"Process {process_id}: Successfully got executable path: {executable_path}")
        return True
    except Exception as e:
        print(f"Process {process_id}: Error: {e}")
        return False

def main():
    if len(sys.argv) != 2:
        print("Usage: python test_orbita_lock.py <major_version>")
        print("Example: python test_orbita_lock.py 132")
        sys.exit(1)
    
    major_version = int(sys.argv[1])
    num_processes = 3
    
    print(f"Testing Orbita download locking with {num_processes} concurrent processes for version {major_version}")
    print("This will test if multiple processes can safely download the same Orbita version without conflicts.")
    
    processes = []
    results = multiprocessing.Manager().list()
    
    start_time = time.time()
    
    for i in range(num_processes):
        p = multiprocessing.Process(target=lambda i=i: results.append(test_download(major_version, i)))
        processes.append(p)
        p.start()
        time.sleep(0.1)
    
    for p in processes:
        p.join()
    
    end_time = time.time()
    total_time = end_time - start_time
    
    print(f"\nTest completed in {total_time:.2f} seconds")
    print(f"Results: {len(results)} processes completed")
    
    success_count = sum(1 for result in results if result)
    print(f"Successful downloads: {success_count}/{num_processes}")
    
    if success_count == num_processes:
        print("✅ All processes completed successfully - locking mechanism is working!")
    else:
        print("❌ Some processes failed - there may be an issue with the locking mechanism")

if __name__ == "__main__":
    main()

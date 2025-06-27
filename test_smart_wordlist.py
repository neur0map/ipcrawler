#!/usr/bin/env python3
"""
Test script to demonstrate Smart Wordlist Selector functionality
"""

from ipcrawler.wordlists import init_wordlist_manager
from ipcrawler.smart_wordlist_selector import SmartWordlistSelector
import os

def test_smart_wordlist_selector():
    print("🧪 Testing Smart Wordlist Selector")
    print("=" * 50)
    
    # Initialize wordlist manager
    try:
        wm = init_wordlist_manager('/Users/carlosm/.config/ipcrawler')
        config = wm.load_config()
        seclists_base = config.get('detected_paths', {}).get('seclists_base')
        
        if not seclists_base:
            print("❌ SecLists not detected - updating...")
            wm.update_detected_paths()
            config = wm.load_config()
            seclists_base = config.get('detected_paths', {}).get('seclists_base')
        
        print(f"📍 SecLists location: {seclists_base}")
        print()
        
        if not seclists_base or not os.path.exists(seclists_base):
            print("❌ SecLists not found - install with: make install")
            return
            
        # Test Smart Wordlist Selector
        selector = SmartWordlistSelector(seclists_base)
        
        # Test scenarios
        test_cases = [
            ("WordPress site", {"wordpress", "wp"}),
            ("PHP application", {"php"}),
            ("Django/Python app", {"django", "python"}),
            ("Drupal CMS", {"drupal"}),
            ("ASP.NET site", {"asp", "aspx"}),
            ("No technology detected", set())
        ]
        
        print("🎯 Testing technology-specific wordlist selection:")
        print()
        
        for scenario, technologies in test_cases:
            print(f"Scenario: {scenario}")
            print(f"Technologies: {technologies if technologies else '(none)'}")
            
            # Test with Smart Wordlist Selector
            smart_result = selector.select_wordlist('web_directories', technologies)
            
            # Test fallback (what would happen without smart selector)
            fallback_result = wm.get_wordlist_path('web_directories', size='default')
            
            if smart_result:
                filename = os.path.basename(smart_result)
                print(f"  🤖 Smart selection: {filename}")
                selection_info = selector.get_selection_info(smart_result, list(technologies)[0] if technologies else 'none')
                print(f"     ↳ {selection_info}")
            else:
                print(f"  🤖 Smart selection: None (no tech-specific wordlist)")
                
            if fallback_result:
                fallback_filename = os.path.basename(fallback_result)
                print(f"  📁 Standard fallback: {fallback_filename}")
            else:
                print(f"  📁 Standard fallback: None")
            
            print()
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_smart_wordlist_selector()
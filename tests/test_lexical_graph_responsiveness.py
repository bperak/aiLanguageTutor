"""
Test file for Lexical Graph Interface Responsiveness

This test suite verifies that the lexical graph interface properly adapts
to different screen sizes and provides a good mobile experience.
"""

import pytest
from playwright.sync_api import sync_playwright, Page, expect
import time


class TestLexicalGraphResponsiveness:
    """Test suite for lexical graph responsive design"""

    @pytest.fixture(scope="class")
    def browser_context(self):
        """Setup browser context for testing"""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context(
                viewport={'width': 1280, 'height': 720},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            page = context.new_page()
            yield page, context, browser
            browser.close()

    @pytest.fixture
    def page(self, browser_context):
        """Get page instance"""
        page, context, browser = browser_context
        return page

    def test_mobile_search_controls_layout(self, page: Page):
        """Test that search controls are compact on mobile"""
        # Set mobile viewport
        page.set_viewport_size({"width": 375, "height": 667})
        
        # Navigate to lexical graph page
        page.goto("http://localhost:3000/lexical/graph")
        
        # Wait for page to load
        page.wait_for_selector("h1:has-text('Lexical Graph')")
        
        # Verify search controls are in grid layout
        search_container = page.locator("div:has-text('Center word:')").first
        expect(search_container).to_be_visible()
        
        # Check that controls are properly stacked on mobile
        center_word_input = page.locator("input[placeholder='Enter kanji/hiragana']")
        expect(center_word_input).to_be_visible()
        
        # Verify compact spacing
        search_section = page.locator("div:has-text('Compact Search Controls')")
        expect(search_section).to_have_class("p-3")

    def test_desktop_search_controls_layout(self, page: Page):
        """Test that search controls expand properly on desktop"""
        # Set desktop viewport
        page.set_viewport_size({"width": 1280, "height": 720})
        
        # Navigate to lexical graph page
        page.goto("http://localhost:3000/lexical/graph")
        
        # Wait for page to load
        page.wait_for_selector("h1:has-text('Lexical Graph')")
        
        # Verify search controls are in expanded layout
        search_container = page.locator("div:has-text('Compact Search Controls')")
        expect(search_container).to_have_class("p-4")
        
        # Check that all controls are visible in a row
        controls = page.locator("div:has-text('Center word:'), div:has-text('Field:'), div:has-text('Depth:'), div:has-text('Color by:')")
        expect(controls).to_have_count(4)

    def test_mobile_search_info_display(self, page: Page):
        """Test that search information is displayed above graph on mobile"""
        # Set mobile viewport
        page.set_viewport_size({"width": 375, "height": 667})
        
        # Navigate to lexical graph page
        page.goto("http://localhost:3000/lexical/graph")
        
        # Wait for page to load
        page.wait_for_selector("h1:has-text('Lexical Graph')")
        
        # Search for a term to populate search info
        page.fill("input[placeholder='Enter kanji/hiragana']", "日本")
        page.click("button:has-text('Search')")
        
        # Wait for search info to appear
        time.sleep(2)
        
        # Verify search info is displayed above graph on mobile
        search_info = page.locator("div:has-text('Nodes:'), div:has-text('Links:'), div:has-text('Term:'), div:has-text('Field:')")
        expect(search_info).to_have_count(4)

    def test_desktop_sidebar_layout(self, page: Page):
        """Test that sidebars are properly displayed on desktop"""
        # Set desktop viewport
        page.set_viewport_size({"width": 1280, "height": 720})
        
        # Navigate to lexical graph page
        page.goto("http://localhost:3000/lexical/graph")
        
        # Wait for page to load
        page.wait_for_selector("h1:has-text('Lexical Graph')")
        
        # Search for a term to populate the graph
        page.fill("input[placeholder='Enter kanji/hiragana']", "日本")
        page.click("button:has-text('Search')")
        
        # Wait for graph to load
        time.sleep(3)
        
        # Verify sidebars are visible on desktop
        selected_node_panel = page.locator("h3:has-text('Selected Node')")
        expect(selected_node_panel).to_be_visible()
        
        settings_panel = page.locator("h3:has-text('Settings')")
        expect(settings_panel).to_be_visible()

    def test_mobile_collapsible_node_details(self, page: Page):
        """Test that node details are collapsible on mobile"""
        # Set mobile viewport
        page.set_viewport_size({"width": 375, "height": 667})
        
        # Navigate to lexical graph page
        page.goto("http://localhost:3000/lexical/graph")
        
        # Wait for page to load
        page.wait_for_selector("h1:has-text('Lexical Graph')")
        
        # Search for a term to populate the graph
        page.fill("input[placeholder='Enter kanji/hiragana']", "日本")
        page.click("button:has-text('Search')")
        
        # Wait for graph to load
        time.sleep(3)
        
        # Verify collapsible node details panel exists
        node_details_summary = page.locator("summary:has-text('Click a node to see details')")
        expect(node_details_summary).to_be_visible()
        
        # Click to expand
        node_details_summary.click()
        
        # Verify content is expanded
        node_details_content = page.locator("div:has-text('No node selected')")
        expect(node_details_content).to_be_visible()

    def test_interactive_neighbors(self, page: Page):
        """Test that neighbor nodes are clickable and update the graph"""
        # Set desktop viewport for better interaction
        page.set_viewport_size({"width": 1280, "height": 720})
        
        # Navigate to lexical graph page
        page.goto("http://localhost:3000/lexical/graph")
        
        # Wait for page to load
        page.wait_for_selector("h1:has-text('Lexical Graph')")
        
        # Search for a term to populate the graph
        page.fill("input[placeholder='Enter kanji/hiragana']", "日本")
        page.click("button:has-text('Search')")
        
        # Wait for graph to load and initial data to populate
        time.sleep(3)
        
        # Wait for neighbors to appear in the sidebar
        neighbors_section = page.locator("h4:has-text('Neighbors (Synonyms)')")
        expect(neighbors_section).to_be_visible()
        
        # Look for any neighbor button (they should be interactive)
        neighbor_buttons = page.locator("button").filter(has_text="POS:")
        expect(neighbor_buttons.first).to_be_visible()
        
        # Get the text of the first neighbor to verify it changes
        first_neighbor_text = neighbor_buttons.first.text_content()
        
        # Click on the first neighbor button
        neighbor_buttons.first.click()
        
        # Wait for the loading state to appear
        loading_indicator = page.locator("div:has-text('Loading new graph...')").first
        expect(loading_indicator).to_be_visible()
        
        # Wait for loading to complete and new graph to load
        time.sleep(3)
        
        # Verify that the loading indicator is gone
        expect(loading_indicator).not_to_be_visible()
        
        # Verify that the graph data has been updated
        # Look for the graph info overlay that shows node/link counts
        graph_info = page.locator("div:has-text('Loaded')").first
        expect(graph_info).to_be_visible()
        
        # Verify that the search info has been updated
        # The search info should show the new term and updated counts
        search_info_container = page.locator("div:has-text('Nodes:'), div:has-text('Links:'), div:has-text('Term:'), div:has-text('Field:')")
        expect(search_info_container).to_have_count(4)
        
        # Check that the term has changed from the original "日本"
        term_info = page.locator("div:has-text('Term:')").first
        expect(term_info).to_be_visible()
        expect(term_info).not_to_contain_text("日本")

    def test_responsive_breakpoints(self, page: Page):
        """Test that responsive breakpoints work correctly"""
        # Test small mobile
        page.set_viewport_size({"width": 320, "height": 568})
        page.goto("http://localhost:3000/lexical/graph")
        page.wait_for_selector("h1:has-text('Lexical Graph')")
        
        # Verify mobile layout
        search_controls = page.locator("div:has-text('Compact Search Controls')")
        expect(search_controls).to_have_class("p-3")
        
        # Test medium mobile
        page.set_viewport_size({"width": 768, "height": 1024})
        page.reload()
        page.wait_for_selector("h1:has-text('Lexical Graph')")
        
        # Verify tablet layout
        search_controls = page.locator("div:has-text('Compact Search Controls')")
        expect(search_controls).to_have_class("p-4")
        
        # Test desktop
        page.set_viewport_size({"width": 1280, "height": 720})
        page.reload()
        page.wait_for_selector("h1:has-text('Lexical Graph')")
        
        # Verify desktop layout
        search_controls = page.locator("div:has-text('Compact Search Controls')")
        expect(search_controls).to_have_class("p-4")

    def test_search_controls_functionality(self, page: Page):
        """Test that all search controls work properly"""
        # Set desktop viewport
        page.set_viewport_size({"width": 1280, "height": 720})
        
        # Navigate to lexical graph page
        page.goto("http://localhost:3000/lexical/graph")
        
        # Wait for page to load
        page.wait_for_selector("h1:has-text('Lexical Graph')")
        
        # Test center word input
        center_input = page.locator("input[placeholder='Enter kanji/hiragana']")
        center_input.fill("新しい")
        expect(center_input).to_have_value("新しい")
        
        # Test search field dropdown
        field_select = page.locator("select")
        field_select.select_option("hiragana")
        expect(field_select).to_have_value("hiragana")
        
        # Test depth dropdown
        depth_select = page.locator("select").nth(1)
        depth_select.select_option("2")
        expect(depth_select).to_have_value("2")
        
        # Test color by dropdown
        color_select = page.locator("select").nth(2)
        color_select.select_option("pos")
        expect(color_select).to_have_value("pos")
        
        # Test exact match checkbox
        exact_checkbox = page.locator("input[type='checkbox']")
        exact_checkbox.check()
        expect(exact_checkbox).to_be_checked()
        
        # Test search button
        search_button = page.locator("button:has-text('Search')")
        expect(search_button).to_be_enabled()
        
        # Test 3D toggle button
        toggle_button = page.locator("button:has-text('3D')")
        expect(toggle_button).to_be_enabled()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

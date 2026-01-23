#!/usr/bin/env node

/**
 * Integration Test Script
 * Tests the connection between frontend and backend
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

console.log('🧪 Testing FEAST Backend Integration...\n');
console.log(`API URL: ${API_URL}\n`);

async function testEndpoint(name, url, options = {}) {
  try {
    console.log(`Testing ${name}...`);
    const response = await fetch(url, options);
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    const data = await response.json();
    console.log(`✅ ${name} - SUCCESS`);
    return { success: true, data };
  } catch (error) {
    console.log(`❌ ${name} - FAILED: ${error.message}`);
    return { success: false, error: error.message };
  }
}

async function runTests() {
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');
  
  // Test 1: Root endpoint
  await testEndpoint('Root Endpoint', `${API_URL}/`);
  console.log('');
  
  // Test 2: Health check
  const healthResult = await testEndpoint('Health Check', `${API_URL}/health`);
  if (healthResult.success) {
    console.log(`   Status: ${healthResult.data.status}`);
    console.log(`   Quota Remaining: ${healthResult.data.quota_remaining}`);
  }
  console.log('');
  
  // Test 3: Quota endpoint
  const quotaResult = await testEndpoint('Quota Check', `${API_URL}/quota`);
  if (quotaResult.success) {
    console.log(`   Remaining: ${quotaResult.data.remaining}/${quotaResult.data.daily_limit}`);
    console.log(`   Status: ${quotaResult.data.status}`);
  }
  console.log('');
  
  // Test 4: Chat endpoint
  const chatResult = await testEndpoint(
    'Chat Endpoint', 
    `${API_URL}/chat`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: 'I want pasta',
        conversation_history: [],
        context: {}
      })
    }
  );
  if (chatResult.success) {
    console.log(`   Message: ${chatResult.data.message.substring(0, 60)}...`);
    console.log(`   Recipes: ${chatResult.data.recipes.length}`);
  }
  console.log('');
  
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');
  console.log('✨ Tests Complete!\n');
  console.log('If all tests passed, your backend is properly connected.');
  console.log('Run `npm run dev` to start the frontend.\n');
}

// Run tests
runTests().catch(console.error);

Here's a systematic approach to test your installation and update process:

## Installation & Update Testing

**Testing Process**

- Create a new virtual machine or clean Windows installation
- Install Python 3.8+ from python.org
- Copy your entire project to the VM
- Run the test script to verify both fresh installation and updates work
- The script will:
  1. Test fresh installation by creating a clean environment
  2. Simulate user input for API keys
  3. Verify venv and .env are created correctly
  4. Test update process by creating mock user data
  5. Run the update process
  6. Verify user data is preserved

**Additional Manual Testing**

After automated tests pass:
1. Test the actual app launch after fresh install
2. Create some real transcription history
3. Customize some settings
4. Run an update
5. Verify everything still works and no settings were lost
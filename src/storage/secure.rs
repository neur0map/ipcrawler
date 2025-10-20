use anyhow::{Context, Result};
use aes_gcm::{Aes256Gcm, Key, Nonce, KeyInit};
use aes_gcm::aead::Aead;
use rand::Rng;
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::PathBuf;
use dirs::home_dir;

#[derive(Debug, Serialize, Deserialize)]
struct EncryptedData {
    nonce: Vec<u8>,
    ciphertext: Vec<u8>,
}

#[derive(Clone)]
pub struct SecureKeyStore {
    key_file: PathBuf,
    encryption_key: Key<Aes256Gcm>,
}

impl SecureKeyStore {
    pub fn new() -> Result<Self> {
        let mut key_file = home_dir().context("Could not find home directory")?;
        key_file.push(".ipcrawler");
        key_file.push("keys.enc");

        // Create directory if it doesn't exist
        if let Some(parent) = key_file.parent() {
            fs::create_dir_all(parent)?;
        }

        // Generate or load encryption key
        let encryption_key = Self::get_or_create_encryption_key()?;

        Ok(SecureKeyStore {
            key_file,
            encryption_key,
        })
    }

    fn get_or_create_encryption_key() -> Result<Key<Aes256Gcm>> {
        let mut key_file = home_dir().context("Could not find home directory")?;
        key_file.push(".ipcrawler");
        key_file.push(".key");

        if key_file.exists() {
            let key_data = fs::read(&key_file)?;
            if key_data.len() == 32 {
                return Ok(*Key::<Aes256Gcm>::from_slice(&key_data));
            }
        }

        // Generate new key
        let mut key_bytes = [0u8; 32];
        rand::thread_rng().fill(&mut key_bytes);
        
        // Ensure directory exists
        if let Some(parent) = key_file.parent() {
            fs::create_dir_all(parent)?;
        }
        
        fs::write(&key_file, &key_bytes)?;
        
        // Set file permissions (read/write only for owner)
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            let mut perms = fs::metadata(&key_file)?.permissions();
            perms.set_mode(0o600);
            fs::set_permissions(&key_file, perms)?;
        }

        Ok(*Key::<Aes256Gcm>::from_slice(&key_bytes))
    }

    fn encrypt_data(&self, data: &str) -> Result<EncryptedData> {
        let cipher = Aes256Gcm::new(&self.encryption_key);
        let mut nonce_bytes = [0u8; 12];
        rand::thread_rng().fill(&mut nonce_bytes);
        let nonce = *Nonce::from_slice(&nonce_bytes);
        
        let ciphertext = cipher
            .encrypt(&nonce, data.as_bytes())
            .map_err(|e| anyhow::anyhow!("Encryption failed: {}", e))?;

        Ok(EncryptedData {
            nonce: nonce_bytes.to_vec(),
            ciphertext,
        })
    }

    fn decrypt_data(&self, encrypted: &EncryptedData) -> Result<String> {
        let cipher = Aes256Gcm::new(&self.encryption_key);
        let nonce = *Nonce::from_slice(&encrypted.nonce);
        
        let plaintext = cipher
            .decrypt(&nonce, encrypted.ciphertext.as_ref())
            .map_err(|e| anyhow::anyhow!("Decryption failed: {}", e))?;

        String::from_utf8(plaintext).map_err(|e| anyhow::anyhow!("Invalid UTF-8: {}", e))
    }

    fn load_keys(&self) -> Result<std::collections::HashMap<String, String>> {
        if !self.key_file.exists() {
            return Ok(std::collections::HashMap::new());
        }

        let encrypted_data = fs::read(&self.key_file)?;
        let encrypted: EncryptedData = bincode::deserialize(&encrypted_data)
            .map_err(|e| anyhow::anyhow!("Failed to deserialize encrypted data: {}", e))?;

        let json_data = self.decrypt_data(&encrypted)?;
        let keys: std::collections::HashMap<String, String> = serde_json::from_str(&json_data)
            .map_err(|e| anyhow::anyhow!("Failed to parse keys: {}", e))?;

        Ok(keys)
    }

    fn save_keys(&self, keys: &std::collections::HashMap<String, String>) -> Result<()> {
        let json_data = serde_json::to_string(keys)?;
        let encrypted = self.encrypt_data(&json_data)?;
        let serialized = bincode::serialize(&encrypted)
            .map_err(|e| anyhow::anyhow!("Failed to serialize encrypted data: {}", e))?;

        fs::write(&self.key_file, serialized)?;

        // Set file permissions
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            let mut perms = fs::metadata(&self.key_file)?.permissions();
            perms.set_mode(0o600);
            fs::set_permissions(&self.key_file, perms)?;
        }

        Ok(())
    }

    pub fn store_key(&self, provider: &str, api_key: &str) -> Result<()> {
        let mut keys = self.load_keys()?;
        keys.insert(provider.to_string(), api_key.to_string());
        self.save_keys(&keys)?;
        Ok(())
    }

    pub fn get_key(&self, provider: &str) -> Result<Option<String>> {
        let keys = self.load_keys()?;
        Ok(keys.get(provider).cloned())
    }

    pub fn remove_key(&self, provider: &str) -> Result<()> {
        let mut keys = self.load_keys()?;
        keys.remove(provider);
        self.save_keys(&keys)?;
        Ok(())
    }

    
}

#[cfg(test)]
mod tests {
    use super::*;
    

    #[test]
    fn test_key_storage() -> Result<()> {
        // Note: These tests would need to be adapted to work with the actual keyring
        // For now, we'll just test the basic functionality
        let store = SecureKeyStore::new()?;
        
        store.store_key("test_provider", "test_key_123")?;
        let retrieved = store.get_key("test_provider")?;
        
        assert_eq!(retrieved, Some("test_key_123".to_string()));
        
        store.remove_key("test_provider")?;
        let retrieved_after_removal = store.get_key("test_provider")?;
        
        assert_eq!(retrieved_after_removal, None);
        
        Ok(())
    }
}
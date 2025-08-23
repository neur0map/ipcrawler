use anyhow::Result;
use std::path::Path;

#[cfg(feature = "dev-tools")]
mod dev_validation {
    use super::*;
    use jsonschema::{Draft, JSONSchema};
    use schemars::{schema_for, JsonSchema};
    use serde::{Deserialize, Serialize};
    use serde_json::Value;
    use std::collections::HashMap;
    use std::fs;
    use thiserror::Error;
    use validator::Validate;

    #[derive(Error, Debug)]
    pub enum ValidationError {
        #[error("Schema validation failed: {0}")]
        SchemaError(String),
        
        #[error("YAML parsing error: {0}")]
        YamlError(#[from] serde_yaml::Error),
        
        #[error("JSON schema error: {0}")]
        JsonSchemaError(String),
        
        #[error("File I/O error: {0}")]
        IoError(#[from] std::io::Error),
        
        #[error("Validation failed: {0}")]
        ValidationFailed(String),
    }

    /// Validates YAML configuration files against a JSON schema
    pub struct YamlValidator {
        schema: JSONSchema,
    }

    impl YamlValidator {
        /// Create a new validator from a schema
        pub fn new(schema_json: &Value) -> Result<Self, ValidationError> {
            let compiled = JSONSchema::options()
                .with_draft(Draft::Draft7)
                .compile(schema_json)
                .map_err(|e| ValidationError::JsonSchemaError(e.to_string()))?;
            
            Ok(Self { schema: compiled })
        }
        
        /// Validate a YAML string against the schema
        pub fn validate_yaml(&self, yaml_str: &str) -> Result<(), ValidationError> {
            let yaml_value: Value = serde_yaml::from_str(yaml_str)?;
            self.validate_json(&yaml_value)
        }
        
        /// Validate a JSON value against the schema
        pub fn validate_json(&self, json_value: &Value) -> Result<(), ValidationError> {
            let result = self.schema.validate(json_value);
            
            if let Err(errors) = result {
                let error_messages: Vec<String> = errors
                    .map(|error| format!("{}: {}", error.instance_path, error))
                    .collect();
                
                return Err(ValidationError::SchemaError(error_messages.join(", ")));
            }
            
            Ok(())
        }
    }

    /// Configuration schema for tools.yaml
    #[derive(Debug, Clone, Serialize, Deserialize, JsonSchema, Validate)]
    pub struct ToolsConfig {
        #[validate(length(min = 1))]
        pub tools: HashMap<String, ToolDefinition>,
        
        pub generic_patterns: Option<Vec<PatternDefinition>>,
    }

    #[derive(Debug, Clone, Serialize, Deserialize, JsonSchema, Validate)]
    pub struct ToolDefinition {
        #[validate(length(min = 1, max = 100))]
        pub name: String,
        
        #[validate(length(min = 1, max = 100))]
        pub command: String,
        
        pub patterns: Option<Vec<PatternDefinition>>,
        
        pub install: Option<InstallInstructions>,
    }

    #[derive(Debug, Clone, Serialize, Deserialize, JsonSchema, Validate)]
    pub struct PatternDefinition {
        #[validate(length(min = 1, max = 100))]
        pub name: String,
        
        #[validate(length(min = 1))]
        pub regex: String,
        
        #[serde(rename = "type")]
        pub pattern_type: String,
        
        #[validate(range(min = 0.0, max = 1.0))]
        pub confidence: Option<f64>,
    }

    #[derive(Debug, Clone, Serialize, Deserialize, JsonSchema)]
    pub struct InstallInstructions {
        pub generic: Option<String>,
        pub macos: Option<String>,
        pub ubuntu: Option<String>,
        pub fedora: Option<String>,
        pub windows: Option<String>,
    }
}

#[cfg(feature = "dev-tools")]
pub use dev_validation::*;


/// Memory safety validator - always available for production safety
pub struct MemoryValidator;

impl MemoryValidator {
    /// Check for potential memory issues in collections
    pub fn validate_collection_size<T>(collection: &[T], max_size: usize) -> Result<()> {
        if collection.len() > max_size {
            return Err(anyhow::anyhow!(
                "Collection size {} exceeds maximum {}",
                collection.len(),
                max_size
            ));
        }
        Ok(())
    }
    
    /// Validate string doesn't contain null bytes
    pub fn validate_string(s: &str) -> Result<()> {
        if s.contains('\0') {
            return Err(anyhow::anyhow!("String contains null bytes"));
        }
        Ok(())
    }
    
    /// Check for reasonable file sizes before reading
    pub fn validate_file_size(path: &Path, max_size: u64) -> Result<()> {
        let metadata = std::fs::metadata(path)?;
        if metadata.len() > max_size {
            return Err(anyhow::anyhow!(
                "File {} exceeds maximum size {} bytes",
                path.display(),
                max_size
            ));
        }
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_memory_validator() {
        // Test string validation
        assert!(MemoryValidator::validate_string("normal string").is_ok());
        assert!(MemoryValidator::validate_string("string\0with\0nulls").is_err());
        
        // Test collection size validation
        let small_vec = vec![1, 2, 3];
        assert!(MemoryValidator::validate_collection_size(&small_vec, 10).is_ok());
        assert!(MemoryValidator::validate_collection_size(&small_vec, 2).is_err());
    }
    
    #[cfg(feature = "dev-tools")]
    #[test]
    fn test_yaml_validator() {
        let schema = serde_json::json!({
            "type": "object",
            "properties": {
                "name": {"type": "string"}
            }
        });
        
        if let Ok(validator) = YamlValidator::new(&schema) {
            let valid_yaml = "name: test";
            assert!(validator.validate_yaml(valid_yaml).is_ok());
            
            let invalid_yaml = "name: 123"; // number instead of string
            assert!(validator.validate_yaml(invalid_yaml).is_err());
        }
    }
}
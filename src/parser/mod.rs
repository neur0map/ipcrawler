mod consistency;
pub mod extractor;
pub mod llm;

pub use extractor::{EntityExtractor, ExtractedEntities, PortInfo, Vulnerability};
pub use llm::LlmParser;

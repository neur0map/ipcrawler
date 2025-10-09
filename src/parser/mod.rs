pub mod llm;
pub mod extractor;
mod consistency;

pub use llm::LlmParser;
pub use extractor::{EntityExtractor, ExtractedEntities, PortInfo, Vulnerability};

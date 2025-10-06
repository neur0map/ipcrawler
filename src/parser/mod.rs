pub mod llm;
pub mod extractor;

pub use llm::LlmParser;
pub use extractor::{EntityExtractor, ExtractedEntities, PortInfo, Vulnerability};

use criterion::{criterion_group, criterion_main, Criterion};

fn parser_benchmarks(_c: &mut Criterion) {
    // TODO: Implement when crate structure allows it
}

fn discovery_extraction_benchmarks(_c: &mut Criterion) {
    // TODO: Implement when crate structure allows it
}

criterion_group!(benches, parser_benchmarks, discovery_extraction_benchmarks);
criterion_main!(benches);
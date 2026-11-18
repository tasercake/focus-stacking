fn branch(value: bool) -> u8 {
    if value {
        covered()
    } else {
        uncovered()
    }
}

fn covered() -> u8 { 42 }

fn uncovered() -> u8 { 83 }

fn main() {
    println!("{}", branch(std::env::args().nth(1).is_some()));
    std::thread::park();
}

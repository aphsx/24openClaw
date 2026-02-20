/// Static filter: เหรียญที่ผ่านเกณฑ์เบื้องต้น
/// ใน Phase 0 ใช้ hardcoded list จาก config
/// Phase 1+ จะดึงจาก exchange API อัตโนมัติ
pub fn get_universe(config_symbols: &[String]) -> Vec<String> {
    config_symbols.to_vec()
}

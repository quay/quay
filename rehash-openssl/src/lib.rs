use std::{borrow::Cow, collections::HashMap};

use pyo3::prelude::*;

#[pyclass(module = "rehash_openssl", name = "sha256")]
struct Sha256 {
    hasher: openssl::sha::Sha256,
}

#[pymethods]
impl Sha256 {
    #[new]
    fn new() -> Self {
        Sha256 {
            hasher: openssl::sha::Sha256::new(),
        }
    }

    fn update(&mut self, data: &[u8]) {
        self.hasher.update(data);
    }

    fn digest(&mut self) -> Cow<[u8]> {
        let result = self.hasher.clone().finish();
        Cow::Owned(result.to_vec())
    }

    fn hexdigest(&mut self) -> String {
        let result = self.hasher.clone().finish();
        hex::encode(result)
    }

    fn __getstate__(&self, py: Python) -> PyResult<HashMap<String, PyObject>> {
        let state: &[u8] = unsafe {
            std::slice::from_raw_parts(
                &self.hasher as *const openssl::sha::Sha256 as *const u8,
                std::mem::size_of::<openssl::sha::Sha256>(),
            )
        };
        // return a dict that is compatible with rehash
        let mut dict: HashMap<String, PyObject> = HashMap::new();
        dict.insert("name".to_string(), "sha256".into_py(py));
        dict.insert("md_data".to_string(), state.into_py(py));
        Ok(dict)
    }

    fn __setstate__(&mut self, py: Python, state: HashMap<String, PyObject>) -> PyResult<()> {
        let name = state
            .get("name")
            .ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("state does not contain name")
            })?
            .extract::<String>(py)?;
        if name != "sha256" {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                "unsupported hash type {}",
                name
            )));
        }

        let md_data = state
            .get("md_data")
            .ok_or_else(|| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>("state does not contain md_data")
            })?
            .extract::<&[u8]>(py)?;
        let len = md_data.len();
        const SHA256_SIZE: usize = std::mem::size_of::<openssl::sha::Sha256>();
        const POINTER_SIZE: usize = std::mem::size_of::<*const ()>();
        // rehash incorrectly adds extra 8 bytes to md_data
        if len != SHA256_SIZE && len != SHA256_SIZE + POINTER_SIZE {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "md_data has wrong size",
            ));
        }
        let md_data = md_data.as_ptr() as *const openssl::sha::Sha256;
        self.hasher = unsafe { std::ptr::read(md_data) };
        Ok(())
    }
}

#[pymodule]
fn rehash_openssl(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<Sha256>()?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_sha256_ctx() {
        // To ensure compatibility with future iterations of rehash-openssl for loading states from
        // prior versions, we examine OpenSSL's internal structure to identify any changes in its
        // implementation and determine when updates to this package are needed.
        let hasher = openssl::sha::Sha256::new();
        assert_eq!(std::mem::size_of::<openssl::sha::Sha256>(), std::mem::size_of::<ffi::SHA256_CTX>());

        let ctx = unsafe { std::mem::transmute::<openssl::sha::Sha256, ffi::SHA256_CTX>(hasher) };
        assert_eq!(ffi::SHA_LBLOCK, 16);
        assert_eq!(std::mem::size_of::<ffi::SHA256_CTX>(), (8 + 1 + 1 + 16 + 1 + 1) * 4);

        // The initial hash value from 5.3.3 of http://dx.doi.org/10.6028/NIST.FIPS.180-4
        assert_eq!(ctx.h[0], 0x6a09e667);
        assert_eq!(ctx.h[1], 0xbb67ae85);
        assert_eq!(ctx.h[2], 0x3c6ef372);
        assert_eq!(ctx.h[3], 0xa54ff53a);
        assert_eq!(ctx.h[4], 0x510e527f);
        assert_eq!(ctx.h[5], 0x9b05688c);
        assert_eq!(ctx.h[6], 0x1f83d9ab);
        assert_eq!(ctx.h[7], 0x5be0cd19);

        // Other fields are zeroed
        assert_eq!(ctx.Nl, 0);
        assert_eq!(ctx.Nh, 0);
        assert_eq!(ctx.data, [0; ffi::SHA_LBLOCK as usize]);
        assert_eq!(ctx.num, 0);

        // The length of the message digest in bytes
        assert_eq!(ctx.md_len, 256/8);
    }

    #[test]
    fn test_get_set_state() {
        pyo3::prepare_freethreaded_python();
        Python::with_gil(|py| {
            let mut hasher = super::Sha256::new();
            hasher.update(b"hello");
            let state = hasher.__getstate__(py).unwrap();
            drop(hasher);

            let mut hasher2 = super::Sha256::new();
            hasher2.__setstate__(py, state).unwrap();
            assert_eq!(hasher2.hexdigest(), "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824");
        });
    }
}

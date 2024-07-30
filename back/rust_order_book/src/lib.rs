use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use std::collections::{BTreeMap, HashMap};
use std::cmp::Ordering;

#[derive(PartialEq, PartialOrd, Clone, Copy)]
struct OrderedFloat(f64);

impl Eq for OrderedFloat {}

impl Ord for OrderedFloat {
    fn cmp(&self, other: &Self) -> Ordering {
        self.0.partial_cmp(&other.0).unwrap_or(Ordering::Equal)
    }
}

#[pyclass]
struct OrderBook {
    bids: BTreeMap<OrderedFloat, Vec<HashMap<String, PyObject>>>,
    asks: BTreeMap<OrderedFloat, Vec<HashMap<String, PyObject>>>,
    all_orders: HashMap<String, HashMap<String, PyObject>>,
}

#[pymethods]
impl OrderBook {
    #[new]
    fn new() -> Self {
        OrderBook {
            bids: BTreeMap::new(),
            asks: BTreeMap::new(),
            all_orders: HashMap::new(),
        }
    }

    fn __getitem__(&self, py: Python, key: &str) -> PyResult<PyObject> {
        match key {
            "bids" => {
                let result: Vec<_> = self.bids.iter().rev().map(|(&OrderedFloat(price), orders)| {
                    let sum: f64 = orders.iter().map(|order| order["amount"].extract::<f64>(py).unwrap()).sum();
                    let dict = PyDict::new(py);
                    dict.set_item("x", price).unwrap();
                    dict.set_item("y", sum).unwrap();
                    dict.to_object(py)
                }).collect();
                Ok(PyList::new(py, result).to_object(py))
            },
            "asks" => {
                let result: Vec<_> = self.asks.iter().map(|(&OrderedFloat(price), orders)| {
                    let sum: f64 = orders.iter().map(|order| order["amount"].extract::<f64>(py).unwrap()).sum();
                    let dict = PyDict::new(py);
                    dict.set_item("x", price).unwrap();
                    dict.set_item("y", sum).unwrap();
                    dict.to_object(py)
                }).collect();
                Ok(PyList::new(py, result).to_object(py))
            },
            _ => {
                self.all_orders.get(key)
                    .map(|order| order.clone().into_py(py))
                    .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyKeyError, _>("Order not found"))
            }
        }
    }

    fn __setitem__(&mut self, py: Python, key: &str, value: PyObject) -> PyResult<()> {
        let order_dict: HashMap<String, PyObject> = value.extract(py)?;
        self.all_orders.insert(key.to_string(), order_dict);
        Ok(())
    }

    fn place_order(&mut self, py: Python, mut order_dict: HashMap<String, PyObject>) -> PyResult<HashMap<String, PyObject>> {
        let order_id = order_dict["id"].extract::<String>(py)?;
        
        order_dict.insert("status".to_string(), "active".into_py(py));
        
        self.all_orders.insert(order_id.clone(), order_dict.clone());

        let price = OrderedFloat(order_dict["price"].extract::<f64>(py)?);
        let order_type = order_dict["order_type"].extract::<i32>(py)?;

        if order_type == 1 { // BID
            self.bids.entry(price).or_insert_with(Vec::new).push(order_dict.clone());
        } else { // ASK
            self.asks.entry(price).or_insert_with(Vec::new).push(order_dict.clone());
        }

        Ok(order_dict)
    }

    fn get_order_book_snapshot(&self, py: Python) -> PyResult<PyObject> {
        let dict = PyDict::new(py);
        dict.set_item("bids", self.__getitem__(py, "bids")?)?;
        dict.set_item("asks", self.__getitem__(py, "asks")?)?;
        Ok(dict.into())
    }

    fn clear(&mut self) {
        self.bids.clear();
        self.asks.clear();
        self.all_orders.clear();
    }

    fn cancel_order(&mut self, py: Python, order_id: &str) -> PyResult<bool> {
        if let Some(order) = self.all_orders.remove(order_id) {
            let price = OrderedFloat(order["price"].extract::<f64>(py)?);
            let order_type = order["order_type"].extract::<i32>(py)?;
    
            let orders = if order_type == 1 { // BID
                self.bids.get_mut(&price)
            } else { // ASK
                self.asks.get_mut(&price)
            };
    
            if let Some(orders) = orders {
                orders.retain(|o| o["id"].extract::<String>(py).unwrap() != order_id);
                if orders.is_empty() {
                    if order_type == 1 {
                        self.bids.remove(&price);
                    } else {
                        self.asks.remove(&price);
                    }
                }
                Ok(true)
            } else {
                Ok(false)
            }
        } else {
            Ok(false)
        }
    }

    fn get_spread(&self) -> PyResult<Option<(f64, f64)>> {
        if let (Some((&OrderedFloat(lowest_ask), _)), Some((&OrderedFloat(highest_bid), _))) = (self.asks.first_key_value(), self.bids.last_key_value()) {
            let spread = lowest_ask - highest_bid;
            let mid_price = (lowest_ask + highest_bid) / 2.0;
            Ok(Some((spread, mid_price)))
        } else {
            Ok(None)
        }
    }

    #[getter]
    fn active_orders(&self, py: Python) -> PyResult<PyObject> {
        let active = self.all_orders.iter()
            .filter(|(_, v)| v["status"].extract::<String>(py).unwrap() == "active")
            .map(|(k, v)| (k.to_string(), v.clone()))
            .collect::<HashMap<_, _>>();
        Ok(active.into_py(py))
    }
    
    #[getter]
    fn all_orders(&self, py: Python) -> PyResult<PyObject> {
        Ok(self.all_orders.clone().into_py(py))
    }

    fn clear_orders(&mut self, py: Python) -> PyResult<Vec<(HashMap<String, PyObject>, HashMap<String, PyObject>, f64)>> {
        let mut matched_orders = Vec::new();
    
        loop {
            let (best_bid, best_ask) = match (self.bids.last_key_value(), self.asks.first_key_value()) {
                (Some((&OrderedFloat(bid), _)), Some((&OrderedFloat(ask), _))) if bid >= ask => (bid, ask),
                _ => break,
            };
    
            let bid = self.bids.get_mut(&OrderedFloat(best_bid)).unwrap().remove(0);
            let ask = self.asks.get_mut(&OrderedFloat(best_ask)).unwrap().remove(0);
            let transaction_price = (best_bid + best_ask) / 2.0;
    
            matched_orders.push((ask.clone(), bid.clone(), transaction_price));
    
            if self.bids.get(&OrderedFloat(best_bid)).map_or(true, |v| v.is_empty()) {
                self.bids.remove(&OrderedFloat(best_bid));
            }
            if self.asks.get(&OrderedFloat(best_ask)).map_or(true, |v| v.is_empty()) {
                self.asks.remove(&OrderedFloat(best_ask));
            }
    
            // Remove from all_orders
            let ask_id = ask["id"].extract::<String>(py)?;
            let bid_id = bid["id"].extract::<String>(py)?;
            self.all_orders.remove(&ask_id);
            self.all_orders.remove(&bid_id);
        }
    
        Ok(matched_orders)
    }
}

#[pymodule]
fn rust_order_book(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<OrderBook>()?;
    Ok(())
}
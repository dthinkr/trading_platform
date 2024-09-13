import { initializeApp } from "firebase/app";
import { getAuth } from "firebase/auth";
import { getAnalytics } from "firebase/analytics";

const firebaseConfig = {
  apiKey: "AIzaSyDCB-Fn5GG6TJUg-msQDlYolrfjCUAE0ys",
  authDomain: "london-trader.firebaseapp.com",
  projectId: "london-trader",
  storageBucket: "london-trader.appspot.com",
  messagingSenderId: "762286058189",
  appId: "1:762286058189:web:d612551587da3ede0d9784",
  measurementId: "G-2Q9M33JGKP"
};

const app = initializeApp(firebaseConfig);
const auth = getAuth(app);

export { auth };
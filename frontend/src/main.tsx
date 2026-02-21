import React from "react";
import ReactDOM from "react-dom/client";
<<<<<<< HEAD
import App from "./App";
=======
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import { AuthProvider } from "./auth";
>>>>>>> origin/main
import "./styles.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
<<<<<<< HEAD
    <App />
=======
    <BrowserRouter>
      <AuthProvider>
        <App />
      </AuthProvider>
    </BrowserRouter>
>>>>>>> origin/main
  </React.StrictMode>
);

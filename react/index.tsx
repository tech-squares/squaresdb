import React from 'react';
import ReactDOM from "react-dom";
import { createRoot } from 'react-dom/client';

const rootElem = document.getElementById('root');
if (rootElem) {
  const root = createRoot(rootElem);
  root.render(
    <h1>Hello, react!</h1>,
  );
}

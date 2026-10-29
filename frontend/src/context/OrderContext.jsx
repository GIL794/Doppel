import { createContext, useContext, useState } from "react";

const OrderContext = createContext(null);

export const OrderProvider = ({ children }) => {
  const [open, setOpen] = useState(false);
  const [prefill, setPrefill] = useState({});

  const openOrder = (data = {}) => {
    setPrefill(data);
    setOpen(true);
  };

  return (
    <OrderContext.Provider value={{ open, setOpen, prefill, openOrder }}>{children}</OrderContext.Provider>
  );
};

export const useOrder = () => useContext(OrderContext);

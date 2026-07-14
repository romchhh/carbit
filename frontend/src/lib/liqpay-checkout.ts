/** Відправка форми на LiqPay Checkout (Client-Server). */
export function submitLiqPayCheckout(checkoutUrl: string, data: string, signature: string) {
  const form = document.createElement("form");
  form.method = "POST";
  form.action = checkoutUrl;
  form.acceptCharset = "utf-8";
  form.style.display = "none";

  const dataInput = document.createElement("input");
  dataInput.type = "hidden";
  dataInput.name = "data";
  dataInput.value = data;
  form.appendChild(dataInput);

  const signInput = document.createElement("input");
  signInput.type = "hidden";
  signInput.name = "signature";
  signInput.value = signature;
  form.appendChild(signInput);

  document.body.appendChild(form);
  form.submit();
}

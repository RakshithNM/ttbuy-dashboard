self.addEventListener("push", (event) => {
  const data = event.data ? event.data.json() : {};
  event.waitUntil(
    self.registration.showNotification(data.title ?? "TTBuy Rate Alert", {
      body: data.body ?? "",
      icon: "/icon-192.png",
      badge: "/icon-192.png",
      data: { url: data.url ?? "https://ttbuyrates.rakshithnettar.com" },
    })
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  event.waitUntil(
    clients.matchAll({ type: "window" }).then((list) => {
      const url = event.notification.data.url;
      const existing = list.find((c) => c.url === url && "focus" in c);
      return existing ? existing.focus() : clients.openWindow(url);
    })
  );
});

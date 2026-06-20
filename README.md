# TimeBudget — Landing Page

Marketing landing page for **TimeBudget**, a web app that treats each day's time like a
bank account: auto-deduct fixed routines (sleep, commute, work), visualize the remaining
disposable time, and surface when you're about to over-commit.

This is a static site — plain HTML/CSS/JS, no build step.

## Local preview

```bash
npm run dev      # python3 -m http.server 5173
```

Then open http://127.0.0.1:5173

## Structure

```
index.html        # the page
src/styles.css    # all styles
src/main.js       # nav toggle, FAQ accordion, scroll reveal
public/assets/    # illustrations
```

## Deploy

Served by GitHub Pages from the `main` branch root.

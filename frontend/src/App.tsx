import Layout from "./components/Layout";
import HomePage from "./pages/HomePage";

/** Root component — renders Layout wrapping HomePage. */
export default function App() {
  return (
    <Layout>
      <HomePage />
    </Layout>
  );
}

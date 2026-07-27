import { PaymentResult } from "@/components/payment-result";

export default async function PaymentResultPage({
  searchParams,
}: {
  searchParams: Promise<{ reference?: string }>;
}) {
  const { reference = "" } = await searchParams;
  return <PaymentResult reference={reference.slice(0, 1000)} />;
}

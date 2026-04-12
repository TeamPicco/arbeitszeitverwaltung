import { createElement } from "react";

import dynamic from "next/dynamic";
import ModuleSkeleton from "../../components/premium/ModuleSkeleton";

export default dynamic(() => import("./HazardModule"), {
  loading: () => createElement(ModuleSkeleton),
  ssr: false,
});

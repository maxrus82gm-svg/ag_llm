// Compile-only independent SDK layout oracle. No main, link, load or API execution.
#include <windows.h>
#include <fwpmu.h>
#include <stddef.h>
static_assert(sizeof(void*)==8,"x64 only");
static_assert(sizeof(FWP_BYTE_BLOB)==16,"blob");
static_assert(sizeof(FWP_VALUE0)==16,"value");
static_assert(offsetof(FWP_VALUE0,uint64)==8,"pointer union alignment");
static_assert(sizeof(FWPM_FILTER_CONDITION0)==40,"condition");
static_assert(offsetof(FWPM_FILTER_CONDITION0,conditionValue)==24,"condition alignment");
static_assert(sizeof(FWPM_ACTION0)==20,"action");
static_assert(sizeof(FWPM_FILTER0)==200,"filter");
static_assert(offsetof(FWPM_FILTER0,providerKey)==40,"provider pointer");
static_assert(offsetof(FWPM_FILTER0,weight)==96,"weight");
static_assert(offsetof(FWPM_FILTER0,filterCondition)==120,"conditions pointer");
static_assert(offsetof(FWPM_FILTER0,action)==128,"action offset");
static_assert(offsetof(FWPM_FILTER0,rawContext)==152,"context union");
static_assert(offsetof(FWPM_FILTER0,filterId)==176,"id offset");
static_assert(offsetof(FWPM_FILTER0,effectiveWeight)==184,"effective weight");
static_assert(sizeof(FWPM_PROVIDER0)==64,"provider");
static_assert(sizeof(FWPM_SUBLAYER0)==72,"sublayer");
static_assert(sizeof(FWPM_SESSION0)==72,"session");
static_assert(FWP_UINT8==1&&FWP_UINT16==2&&FWP_UINT32==3&&FWP_UINT64==4,"integer types");
static_assert(FWP_SECURITY_DESCRIPTOR_TYPE==14,"ALE user SD type, not FWP_SID");
static_assert(FWP_MATCH_EQUAL==0&&FWP_MATCH_NOT_EQUAL==10,"comparators");
static_assert(FWP_ACTION_BLOCK==0x1001&&FWP_ACTRL_MATCH_FILTER==1,"action/access");
